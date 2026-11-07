# Personal Knowledge OS — RAG Project Roadmap

Last updated: 2026-11-04

Current phase: **Phase 15 — RAG pipeline hardening and scale** (15.0 and 15.1 closed; next 15.2)

Detailed working plan (scope, exit criteria, risks): [`docs/architecture/roadmap.md`](../architecture/roadmap.md)

## Goal

A production-ready, enterprise-grade Personal Knowledge Base RAG system: accurate retrieval, grounded and cited answers, measurable quality, secure and reliable operation, full observability, automated delivery, and a usable interface.

## Status legend

| Status | Meaning |
| --- | --- |
| Complete | Delivered and verified |
| Current | In progress |
| Planned | Not started |

## Roadmap at a glance

| Phase | Name | Status |
| --- | --- | --- |
| 1 | Naive RAG | Complete |
| 2 | Advanced RAG | Complete |
| 3 | Agentic RAG foundations | Complete |
| 4–6 | RAG improvements, local models and provider handling | Complete |
| 7 | Observability with Prometheus | Complete |
| 8 | RAG quality | Complete |
| 9 | Security and reliability | Complete |
| 10 | Containerization and CI/CD | Complete |
| 11 | Pre-deployment hardening | Complete |
| 12 | Deployment | Complete |
| 13 | LLMOps foundations | Complete |
| 14 | Human feedback and React frontend | Complete |
| 15 | RAG pipeline hardening and scale | Complete (2026-11-07) |
| 16 | RAG portfolio and reusable eval kit | Current |
| 17 | Multi-tenancy and RBAC | Planned |

## Foundation (Phases 1–6)

### Phase 1 — Naive RAG

- Document ingestion, chunking and embeddings
- Vector store and similarity retrieval
- Grounded answer generation

### Phase 2 — Advanced RAG

- Query processing and rewriting
- Hybrid retrieval: dense vectors plus keyword (BM25)
- Rank fusion and cross-encoder reranking

### Phase 3 — Agentic RAG foundations

- Tool-using agent over the retrieval pipeline
- Agent patterns as a learning milestone

### Phases 4–6 — RAG improvements, local models and provider handling

- Retrieval and generation improvements
- Local model integration (Ollama)
- Multi-provider LLM handling with fallback

## Production engineering (Phases 7–12)

### Phase 7 — Observability with Prometheus

- Application and infrastructure metrics
- Structured JSON logging
- Grafana dashboards (optional profile)

### Phase 8 — RAG quality

- Context sufficiency assessment
- Citation verification
- Confidence scoring and abstention

### Phase 9 — Security and reliability

- API authentication and request/response validation
- Redis rate limiting
- Semantic caching
- Prompt-injection defenses
- Retries, timeouts and provider fallback

### Phase 10 — Containerization and CI/CD

- Docker and Docker Compose
- GitHub Actions pipeline
- Evaluation regression gate in CI

### Phase 11 — Pre-deployment hardening

- Full-codebase security and reliability review
- Lint and static security gates in CI (`ruff`, `bandit`)
- Idempotent ingestion
- Evaluation gate coverage for abstention

### Phase 12 — Deployment

- AWS EC2 with Docker Compose
- Automatic HTTPS with Caddy
- Automated deployment through GitHub Actions and AWS Systems Manager
- Health checks, warm-up and rollback

## LLMOps and product (Phases 13–14)

### Phase 13 — LLMOps foundations (closed 2026-10-29)

| Sub-phase | Name |
| --- | --- |
| 13.0 | Evaluation foundation |
| 13.1 | Test foundation and CI hygiene |
| 13.2 | Prompt versioning |
| 13.3 | Token and cost accounting |
| 13.4 | Observability: request tracing |
| 13.5 | Operational readiness |

#### 13.0 Evaluation foundation

- Versioned golden dataset: normal, difficult, ambiguous, multi-hop, unanswerable and adversarial questions
- Retrieval-relevance labels
- Paired-comparison harness with confidence intervals
- Judge calibration and a frozen held-out test split

#### 13.1 Test foundation and CI hygiene

- Unit, API, API-contract, integration and Redis tests
- Automated test job in CI with a coverage floor
- Dependency pinning, vulnerability scanning and automated dependency updates

#### 13.2 Prompt versioning

- Prompts stored and versioned in the repository
- Prompt version recorded in responses, logs, metrics, cache keys and evaluation runs

#### 13.3 Token and cost accounting

- Per-stage token usage, latency and estimated cost
- Metrics and structured logs

#### 13.4 Observability: request tracing

- Full correlation: one request ID across every pipeline stage, log line and trace
- Per-stage timing and outcome in logs and metrics
- RAG quality metrics: cache hits, abstention, citation-verification failures, empty retrievals
- Cached answers keep their sources, citation check and confidence
- LLM tracing with Langfuse Cloud (free tier) on OpenTelemetry, non-blocking and fail-open, with content masking
- Cardinality rules: high-cardinality data in logs and traces, never in metric labels

#### 13.5 Operational readiness

- Provisional SLOs and error budgets for availability and latency
- Error-budget burn-rate alerts with free notifications through Grafana alerting
- External uptime monitoring
- Docker log rotation and logging/retention policy
- Deployment credentials: least-privilege key with 90-day rotation (short-lived OIDC credentials are blocked by the AWS account's managed policy)
- Container resource limits
- Authorization model
- Index rebuild procedure

### Phase 14 — Human feedback and React frontend

| Sub-phase | Name |
| --- | --- |
| 14.0 | Human feedback endpoint |
| 14.1 | React frontend |

#### 14.0 Human feedback endpoint

- Feedback API tied to request IDs
- Durable feedback storage
- Review path from feedback to evaluation candidates

#### 14.1 React frontend

- Query interface with answers, citations and abstention display
- Streamed answers, with verification and confidence sent after the text
- Feedback controls
- Responsive layout, automated tests and CI build

## Scale (Phase 15)

### Phase 15 — RAG pipeline hardening and scale

| Sub-phase | Name |
| --- | --- |
| 15.0 | Ingestion correctness and PDF upload |
| 15.1 | Full PDF corpus |
| 15.2 | Retrieval tuning and stage ablations |
| 15.3 | Token and cache optimization (dropped 2026-10-31) |
| 15.4 | Final operational validation (closed lite 2026-11-07) |

Scope trimmed 2026-10-31 for a single-user, $0 system: no storage migration now, no research-style comparisons. Detail: `docs/architecture/roadmap.md` Phase 15.

#### 15.0 Ingestion correctness and PDF upload

- Single, consistent ingest and delete path
- BM25 built from Chroma, so keyword and vector indexes cannot drift
- Index and documents on named volumes, seeded from the image
- PDF upload, list and delete from the UI (PR 2)
- Storage choice deferred to the 15.1 measurements, on real-size data

#### 15.1 Full PDF corpus

- Full PDF corpus (100–150 files), indexed and measured; no new formats
- About 20–30 new evaluation questions, plus a spot-check of unreviewed labels

#### 15.2 Retrieval tuning and stage ablations

- Chunking and retrieval settings (retrieval-only, $0)
- HNSW (Chroma default, untuned) vs exact brute-force top-k check ($0)
- Pipeline-stage ablations, including skipping the rewrite for short, clear queries

#### 15.3 Token and cache optimization

- Dropped: one user gives too few repeats for extra cache layers to pay off. Revisit only with log evidence.

#### 15.4 Final operational validation

- Closed as "lite" (owner, 2026-11-07, Groq quota exhausted): torch 2.14.1 in one audited pin file (retrieval identical), report-only Trivy image scan, readiness review filed with its one Medium finding fixed (Caddy body cap)
- Capacity derived from the Groq free tier, not load-tested (accepted): ~3 answered queries/min, ~80/day; k6 script kept
- Provisional SLOs kept; fresh generation baseline and F-29 moved to Phase 16

## Showcase (Phase 16)

### Phase 16 — RAG portfolio and reusable eval kit

- Order (owner, 2026-11-07): the variants first, the eval kit last; early variant numbers are provisional until the kit re-measures them
- 16.0 Naive and Advanced RAG, from the owner's existing folders, updated to the same corpus
- 16.1 Agentic RAG, from its existing folder
- Those folders are moved into this project's root only while being updated, never committed here, then moved out to their own repository
- 16.2 Graph RAG, with multi-hop questions
- 16.3 Multimodal RAG, with image and table questions
- 16.4 Reusable eval kit, extracted from `eval/`; Production RAG reproduces its baseline through it, then every variant is re-measured
- 16.5 One cross-variant comparison table and a README per project
- Production RAG is this live repository, not a frozen snapshot

## Multi-user (Phase 17)

### Phase 17 — Multi-tenancy and RBAC

- Portfolio demo on prod: `c2` split into 5 company tenants, demo keys per role
- API key mapped to a tenant, user and role; principals and document access in SQLite
- Tenant and document permissions enforced before ranking, in the semantic cache key, on `/documents`, traces and feedback
- Roles viewer / editor / admin, plus per-document access inside a tenant
- Supersedes the single-user decision (F-19). Detail: `docs/architecture/roadmap.md` Phase 17

## Learning tracks (outside the production path)

- Kafka and event-driven ingestion
- Kubernetes
- MCP and tool integration
- Multi-agent systems
- ML and model-engineering experiments

## Production-readiness pillars

| Pillar | Phases |
| --- | --- |
| Retrieval quality | 1, 2, 15 |
| Grounded answers and abstention | 8, 15 |
| Evaluation and regression testing | 10, 13, 15 |
| Automated testing and CI quality gates | 10, 11, 13 |
| Security | 9, 11, 13 |
| Reliability | 9, 11, 12, 15 |
| Observability: logs, metrics, traces, correlation, alerts, SLOs | 7, 13, 15 |
| LLMOps: prompts, cost, tracing | 13 |
| Deployment and delivery | 10, 12, 13 |
| User experience and feedback | 14 |
| Scale and capacity | 15 |
