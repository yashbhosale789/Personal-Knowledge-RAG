# Changelog

User-visible and operational changes, newest first. There are no versioned releases: every merge to `main` deploys. Each entry names its roadmap phase; the [roadmap](docs/architecture/roadmap.md) has the evidence, PRs and decisions behind it.

## Unreleased: Phase 15.2, retrieval tuning (in progress)

### Added
- Paired retrieval experiments on corpus `c2`: HNSW vs exact search, chunk size and overlap, page merging, `TOP_K`, rerank pool, BM25 tokenizer.
- `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`, `RAG_CHUNK_MERGE_PAGES` and `RAG_TOP_K` select variants (`c2` only).

### Changed
- Chosen for `c2`: 1024-character chunks, overlap 64, `TOP_K` 3 (MRR better at equal context). Not yet shipped to production.

## 2026-11-04: Phase 15.1, full PDF corpus

### Added
- Corpus `c2`: 236 PDFs from 5 companies (RAG-Multi-Corpus, MIT), selected with `RAG_CORPUS=c2`; stays offline.
- Dataset `v2`: 79 questions (22 new from the upstream query set), and retrieval baselines for `c1` and `c2`.

### Fixed
- Text extraction: ligatures, U+FFFF bullets and capitals split from their word by font kerning are repaired at load time.
- The semantic cache no longer relies on a car-specific word list: a hit needs the same content words in the same order (F-14).
- The injection scanner no longer rejects spec labels such as `Operating System:`.

## 2026-11-03: Phase 15.0, PDF upload and a persistent index

### Added
- Upload, list and delete PDFs from the UI (`/documents`), keyed, rate limited, size-capped and injection-scanned.
- The index and documents live in named volumes, so uploads survive deploys and rollbacks.

## 2026-11-02: Phase 15.0, ingestion correctness

### Fixed
- One ingest path for the API and the batch script; Chroma is the single source of truth and BM25 is rebuilt from it after every write. Documents ingested through the API now reach keyword search, and deleted ones can no longer be retrieved (F-01, F-03, F-27).

## 2026-10-30: Phase 14, feedback and React UI

### Added
- `POST /feedback`: thumbs up/down and a comment, stored in SQLite with the prompt version, model and the chunks used; text deleted after 90 days.
- React + TypeScript UI served from the same origin, with a strict Content-Security-Policy.
- `POST /query/stream`: server-sent token events and a final event with verification and per-chunk sources.
- Chat memory: follow-ups are rewritten into standalone questions using the last 5 turns.
- "Field notes" UI redesign with footnote-style sources and light/dark themes.

## 2026-10-29: Phase 13.5, operational readiness

### Added
- Provisional SLOs with fast- and slow-burn email alerts, plus app-down, provider-failure and fallback-rate alerts.
- External uptime check every 10 minutes; container memory limits; Docker log rotation.

### Changed
- The citation verifier moved to Groq `qwen3.8-27b` (about 1 s instead of 18–24 s) and degrades to a low-confidence answer instead of failing.

### Security
- Committed keys were rotated, and the deploy key is now least privilege with a 90-day rotation.

## 2026-10-28: Phases 13.0, 13.1 and 13.4, evaluation, tests and tracing

### Added
- A versioned golden dataset (`v1`, 57 questions) with a calibrated LLM judge and a failure analysis.
- Offline test suite with contract tests and a coverage floor as a required check; branch protection on `main`.
- One request ID across responses, logs, metrics and Langfuse traces (content masked by default); per-stage latency; RAG quality panels.

## 2026-10-26: Phases 13.2 and 13.3, prompt versioning and token accounting

### Added
- Prompt versions in the cache key and in every eval result, so a prompt or model change never serves an old answer.
- Per-stage token and latency metrics for every LLM call, marked reported or estimated.

## Earlier: Phases 1–12

Naive RAG, then advanced RAG (query rewriting, hybrid retrieval, RRF, cross-encoder reranking), agentic RAG foundations, local Ollama support, Prometheus metrics, context sufficiency and citation verification, Redis rate limiting and semantic caching, prompt-injection defences, Docker and CI/CD, `ruff` and `bandit` gates, and the AWS EC2 deployment with HTTPS, SSM deploys and drilled rollback.
