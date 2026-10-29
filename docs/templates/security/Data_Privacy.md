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
| Feedback comments (Phase 14.0) | Free-text comments. | Proposed 90 days, then deleted; ratings without comments may be kept for evaluation. |

Rules:
- Never log full query, prompt or answer text at INFO or above in the app; snippets are capped at 60 characters.
- Never log secrets or the API key (only its SHA-256 hash is used, for rate limiting).
- Do not send documents you would not give to Langfuse and the LLM providers (Groq, OpenRouter, Gemini): both receive retrieved passages.

## Privacy review checklist
- [ ] Identify whether prompts include retrieved document passages.
- [ ] Identify providers receiving queries, passages, embeddings, or metadata.
- [ ] Review provider retention and training policies before sending sensitive content.
- [ ] Avoid logging full documents or secrets unless strictly required and protected.
- [ ] Define retention and deletion behavior for source files, chunks, vectors, traces, and backups.
- [ ] Restrict access to evaluation datasets and observability systems.
- [ ] Explain limitations to users accurately.

Do not claim data stays entirely on-device or within a particular cloud unless verified end to end.
