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

## Privacy review checklist
- [ ] Identify whether prompts include retrieved document passages.
- [ ] Identify providers receiving queries, passages, embeddings, or metadata.
- [ ] Review provider retention and training policies before sending sensitive content.
- [ ] Avoid logging full documents or secrets unless strictly required and protected.
- [ ] Define retention and deletion behavior for source files, chunks, vectors, traces, and backups.
- [ ] Restrict access to evaluation datasets and observability systems.
- [ ] Explain limitations to users accurately.

Do not claim data stays entirely on-device or within a particular cloud unless verified end to end.
