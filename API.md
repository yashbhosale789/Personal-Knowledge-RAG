# API

FastAPI (`rag-project/api/`). Interactive docs at `/docs` when running locally. Every endpoint except `/health` and `/metrics` needs:

```text
Authorization: Bearer <API_KEY>
```

| Endpoint | Purpose | Public in production |
| --- | --- | --- |
| [`POST /query`](#post-query) | Ask a question, JSON answer | yes |
| [`POST /query/stream`](#post-querystream) | Same, server-sent events | yes |
| [`POST /feedback`](#post-feedback) | Thumbs up/down on an answer | yes |
| [`POST /documents`](#documents) · `GET /documents` · `DELETE /documents/{name}` | Upload, list, delete PDFs | yes |
| [`POST /ingest`](#ingest-local-development) · `DELETE /ingest` | Ingest or delete by server path | no (Caddy 404) |
| [`GET /health`](#get-health) | Readiness | yes |
| [`GET /metrics`](#get-metrics) | Prometheus exposition | no (Caddy 404) |

Examples use `bash`; on PowerShell use `curl.exe` and `$env:API_KEY`.

---

## `POST /query`

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "Where is the spare tyre on the Aventro Sedan?"}'
```

| Field | Type | Notes |
| --- | --- | --- |
| `query` | string, 1–2000 chars | required |
| `provider` | `groq` \| `openrouter` \| `gemini` \| `ollama` | optional override of `PIPELINE_PROVIDER` |
| `return_contexts` | bool | default `true` |
| `history` | up to 5 turns of `{query, rewritten_query?, answer}` (answer ≤ 500 chars) | optional; makes the query a follow-up. Untrusted: used only to rewrite it into a standalone question |

The response (schema pinned by `tests/contracts/query_response.json`):

| Field | Meaning |
| --- | --- |
| `query_id` | request ID; also in logs, metrics and the trace; use it for `/feedback` |
| `query`, `rewritten_query` | as received, and as rewritten for retrieval |
| `answer` | grounded answer with `[SOURCE N]` markers |
| `sources`, `chunks_used` | source file names and number of chunks given to the LLM |
| `sufficiency` | `{sufficient, reason, tier}` from the sufficiency gate |
| `citation_check` | `{grounded, unsupported_claims, reason, tier}` from the verifier |
| `confidence` | `high` or `low` |
| `outcome` | `answer`, `answer_low_confidence`, `abstain`, `empty` or `cached` |
| `provider`, `prompt_version`, `latency_ms`, `timestamp` | provenance and timing |

Errors: `400` empty query, `401` bad key, `502` every provider failed, `503` pipeline not ready.

## `POST /query/stream`

Same body and key. Server-sent events:

```text
event: token
data: {"text": "Loosen the "}        (repeated while the answer is generated)

event: final
data: {...every /query field..., "caveat": null, "chunks": [{"n": 1, "source": "manual.pdf", "page": "2", "snippet": "...", "cited": true}]}
```

- A cache hit, an abstain or an empty retrieval sends only `final`.
- `final.answer` is authoritative (it carries the low-confidence caveat and post-generation fixes), so a client replaces the streamed text with it. `chunks[n-1]` is the chunk behind `[SOURCE n]`.
- A failure sends one `error` event, `{"status": 502, "error": "..."}`, instead of `final`. Providers are retried and fallen back only until the first token.
- Schema pinned by `tests/contracts/query_stream_final.json`.

```bash
curl -N -X POST http://127.0.0.1:8000/query/stream \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{"query": "How do I change a tyre?"}'
```

## `POST /feedback`

Rate an answer within 24 hours, using its `query_id`:

```bash
curl -X POST http://127.0.0.1:8000/feedback \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{"request_id": "<query_id>", "rating": "down", "comment": "Cited the wrong page."}'
```

- `rating` is `up` or `down`; `comment` is optional (at most 1000 characters). Sending again for the same `request_id` replaces both.
- The stored record takes the query, answer, model, prompt version and the source, page and snippet of each chunk from what the server saved for that request, not from the client.
- Errors: `404` unknown or older than 24 hours, `429` above 30 a minute, `503` Redis or the feedback store unavailable. Text is deleted after 90 days.

## Documents

What the UI's Documents panel calls. Upload and delete share a limit of 10 a minute per key.

```bash
curl -X POST http://127.0.0.1:8000/documents -H "Authorization: Bearer $API_KEY" -F "file=@manual.pdf"
curl http://127.0.0.1:8000/documents -H "Authorization: Bearer $API_KEY"
curl -X DELETE http://127.0.0.1:8000/documents/manual.pdf -H "Authorization: Bearer $API_KEY"
```

- **Upload rules:** a plain file name ending in `.pdf` (a name containing a path is rejected, not stripped), a `%PDF-` header, at most 10 MiB and 1,000,000 characters of extracted text.
- The file is saved to the documents folder and ingested through the shared path: injection scan, replace by name, cache clear, BM25 reset. A rejected upload is removed; a rejected same-name upload leaves the old file and its chunks in place.
- **List:** each PDF on disk with its indexed chunk count (0 means nothing is retrievable).
- One document write runs at a time; a second gets `409`.
- Errors: `400` name or header, `404` unknown name on delete, `409` busy, `413` too large, `422` rejected (injection, no text, too long), `429` rate limit.

## Ingest (local development)

Takes a server path under `data/documents/`. Blocked at Caddy in production.

```bash
curl -X POST http://127.0.0.1:8000/ingest \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{"file_path": "data/documents/manual.pdf"}'

curl -X DELETE "http://127.0.0.1:8000/ingest?file_path=data/documents/manual.pdf" \
  -H "Authorization: Bearer $API_KEY"
```

Re-ingesting a path replaces its chunks. Delete removes the chunks and the file, then clears the cache.

## `GET /health`

`{status, version, pipeline_ready, timestamp}`. `status` is `degraded` until the models are loaded and BM25 is built; use it as the readiness check.

## `GET /metrics`

Prometheus exposition: HTTP request counts and latency buckets (the SLO source), provider calls, retries and fallbacks, per-stage latency, and LLM token accounting:

- `llm_tokens_total{stage,provider,model,type,source}`: `type` is `prompt` or `completion`; `source="reported"` is the provider's own count, `source="estimated"` a ~4 characters/token estimate used only when the provider gives none.
- `llm_call_duration_seconds{stage,provider,model}`: latency of each successful call; `_count` is the number of calls.

Under the $0 budget, "cost" means free-tier quota: for example `sum by (provider, model) (increase(llm_tokens_total[1d]))` gives tokens per day.

---

Postman collections for Dev, QA and Prod, and a query suite grouped by question type, are in [`postman/`](postman/).
