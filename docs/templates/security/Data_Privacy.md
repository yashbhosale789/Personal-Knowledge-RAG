# Data Privacy

## Purpose
Document what data the application processes, where it is stored, and which external services may receive it.

## Complete from verified implementation
- Document types and metadata collected:
- Local storage locations:
- Vector-store persistence and deletion behavior:
- External LLM providers:
- External embedding providers:
- External tracing/analytics providers:
- Log and trace fields:
- Backup locations and retention:
- Evaluation dataset contents:
- User data deletion process:

## What is logged and how long it is kept (Phase 13.5 policy, decided 2026-10-29)
Queries can contain sensitive text, so text is kept only where it is needed, and every store has a bound.

| Store | Query/answer text it holds | Retention |
| --- | --- | --- |
| Container logs (Docker `json-file`) | Access log: none (request ID, path, status, latency). Pipeline logs: at most 60 chars of the query and the rewritten query; provider error bodies. | 3 × 10 MB per service (rotation in `docker-compose.prod.yml`), and deleted when the container is recreated, which happens on every app deploy. No off-host shipping. |
| Langfuse Cloud (Hobby, third party) | Full query, full LLM prompts including retrieved passages, full answers. | 30 days of data access on Hobby. Retention management is a paid feature, so deletion after 30 days is not guaranteed: treat anything sent there as kept by a third party. Tracing is fail-open; unset the Langfuse keys to stop sending. |
| Redis semantic cache | Full query, its embedding, answer, sources. | 24 h TTL (`CACHE_TTL_SECONDS`), evicted earlier under `maxmemory` (`volatile-lru`). |
| Redis rate-limit counters | None (key hash only). | 120 s TTL. |
| Prometheus | None: counters/histograms with route, status and provider labels only. | 30 days (`--storage.tsdb.retention.time=30d`, so the 28-day SLO window fits). |
| Grafana | None (dashboards and alert state only). | Until the volume is deleted. |
| Redis feedback grounding (Phase 14.0) | Per `/query` request ID: full query, answer, outcome, prompt version, model, and for each chunk handed to generation its source, page and first 200 chars. Key `feedback:grounding:<request_id>`. | 24 h TTL (`FEEDBACK_GROUNDING_TTL_SECONDS`), evicted earlier under `maxmemory` (`volatile-lru`); after that, `POST /feedback` for that request returns 404. Survives deploys (the deploy flushes only `cache:*`). |
| Feedback store (Phase 14.0): SQLite on the `feedback_data` volume (`/app/feedback/feedback.db`) | One row per rated request: query, answer and comment text, plus rating, outcome, prompt version, model and the chunk sources (source, page, snippet, cited flag). | Query, answer and comment text are set to NULL 90 days after the first rating (`FEEDBACK_RETENTION_DAYS`; the purge runs at app start and on every `POST /feedback`). Rating, request ID, outcome, prompt version, model and chunk sources are kept until the volume is deleted. Survives deploys, rollbacks and container recreation; not backed up. |

Rules:
- Never log full query, prompt or answer text at INFO or above in the app; snippets are capped at 60 characters.
- Never log secrets or the API key (only its SHA-256 hash is used, for rate limiting).
- Do not send documents you would not give to Langfuse and the LLM providers (Groq, OpenRouter, Gemini): both receive retrieved passages.
- Feedback comments are untrusted text: never put them into prompts, render them as plain text only, never log them (the `feedback` log event carries the request ID, rating and whether a comment exists). Feedback stores what the server served for that request ID, never what the client says about the answer.
- Feedback becomes evaluation data only as candidates through `generate_candidates` / `review_candidates` with manual review, never directly into the golden dataset.
- Delete all feedback (cannot be undone; the app is down until the last step): `docker compose -f docker-compose.prod.yml rm -sf app`, then `docker volume rm` on the volume `docker volume ls | grep feedback_data` shows, then start `app` again with `IMAGE_TAG` set.

## Privacy review checklist
- [ ] Identify whether prompts include retrieved document passages.
- [ ] Identify providers receiving queries, passages, embeddings, or metadata.
- [ ] Review provider retention and training policies before sending sensitive content.
- [ ] Avoid logging full documents or secrets unless strictly required and protected.
- [ ] Define retention and deletion behavior for source files, chunks, vectors, traces, and backups.
- [ ] Restrict access to evaluation datasets and observability systems.
- [ ] Explain limitations to users accurately.

Do not claim data stays entirely on-device or within a particular cloud unless verified end to end.
