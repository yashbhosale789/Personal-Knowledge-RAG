# Personal Knowledge OS — RAG Project Roadmap

Last updated: 2026-10-23

Current phase: **Phase 13 — LLMOps foundations**

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
| 13 | LLMOps foundations | Current |
| 14 | Human feedback and React frontend | Planned |
| 15 | RAG pipeline hardening and scale | Planned |
| 16 | Graph RAG and Multimodal RAG | Planned |
| 17 | Portfolio extraction | Planned |

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

### Phase 13 — LLMOps foundations

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

- Request IDs across every pipeline stage
- Per-stage timing and outcome in logs and metrics
- Optional external LLM tracing, non-blocking and fail-open

#### 13.5 Operational readiness

- Alerting rules and notifications
- Short-lived deployment credentials
- Container resource limits
- Authorization model and logging/retention policy
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
- Feedback controls
- Responsive layout, automated tests and CI build

## Scale and advanced RAG (Phases 15–16)

### Phase 15 — RAG pipeline hardening and scale

| Sub-phase | Name |
| --- | --- |
| 15.0 | Ingestion and index lifecycle |
| 15.1 | Corpus scale-up and multi-format ingestion |
| 15.2 | Retrieval and model benchmarking |
| 15.3 | Token optimization |
| 15.4 | Final operational validation |

#### 15.0 Ingestion and index lifecycle

- Single, consistent ingest and delete path
- Persistent, versioned index
- Consistent keyword and vector indexes

#### 15.1 Corpus scale-up and multi-format ingestion

- Full document corpus
- Format-aware loading and chunking
- Expanded evaluation dataset for the full corpus

#### 15.2 Retrieval and model benchmarking

- Chunking, retrieval, reranker and model comparisons
- Pipeline-stage ablations
- Agentic versus deterministic pipeline comparison

#### 15.3 Token optimization

- Prompt and context reduction validated against the evaluation baseline

#### 15.4 Final operational validation

- Load testing and capacity statement
- Service-level objectives and alert thresholds
- Production-readiness review

### Phase 16 — Graph RAG and Multimodal RAG

- Knowledge-graph-based retrieval
- Multimodal document understanding
- Delivered as a standalone project

## Showcase (Phase 17)

### Phase 17 — Portfolio extraction

- Standalone, portfolio-ready artifacts
- Architecture documentation and evaluation write-up
- Shared utilities where justified

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
| Observability | 7, 13 |
| LLMOps: prompts, cost, tracing | 13 |
| Deployment and delivery | 10, 12, 13 |
| User experience and feedback | 14 |
| Scale and capacity | 15 |
