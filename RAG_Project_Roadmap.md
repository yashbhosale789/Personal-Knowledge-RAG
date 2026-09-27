# RAG Project Roadmap

## Status

Phases 1–10 complete. Starting Phase 11.

## Phases 1–5 (Done)

1. Naive RAG — BGE embeddings, Chroma, OpenRouter
2. Advanced RAG — BM25 + dense, RRF, cross-encoder reranker, query rewriter
3. Evaluation — Custom LLM-as-judge, 12-question golden dataset, 4 metrics
4. Agentic RAG — Manual ReAct agent, LangGraph agent, metadata tool
5. FastAPI Backend — /query /ingest /health, async, retries, structured logging, provider fallback

## Phases 6–16 (Planned)

6. Ollama — Local LLM as fourth provider via config switch [DONE]
7. Observability — Prometheus metrics, request/provider tracing [DONE]
8. RAG Quality — Context sufficiency, citation verification, confidence scoring, adversarial eval cases [DONE]
9. Security + Reliability — Redis (rate limiting + semantic caching), prompt injection defense, input/output validation [DONE]
10. Containerization + CI/CD — Dockerfile, docker-compose (app + Redis + Prometheus/Grafana + alerting), GitHub Actions with eval regression gate, scoped code review [DONE]
11. Fixes / Pre-Deployment Hardening — full-codebase security/reliability review; add ruff + bandit to CI; fix `add_chunks` append-not-upsert bug in `store.py` (required); optionally close the CI eval gate's abstention blind spot
12. Deployment — Cloud VM, public URL, auto-deploy on merge
13. LLMOps — Prompt versioning, model benchmarking (reranker comparison experiment), A/B testing, token optimization, human feedback endpoint, Langfuse (self-hosted) for RAG-quality metrics + cost tracking
14. Graph RAG + Multimodal RAG — entity extraction, knowledge graph (NetworkX → Neo4j), graph traversal retrieval, image/table extraction, vision embeddings, multimodal retrieval. NOTE: this is a separate, standalone project ("Multimodal Graph RAG"), not built inside this repo — confirm scope split before starting any code
15. Portfolio Extraction — Standalone sub-projects, shared/ library, benchmark comparisons, documentation, readability-focused code review, deferred multi-tenant document upload work
16. React Frontend — Streaming chat, citations, pipeline switcher, retrieval trace, human feedback UI

## Phases 17–21 (Future)
17. Kafka + EDA — Async ingestion pipeline
18. Kubernetes — Orchestration and scaling
19. MCP — Tool interoperability layer
20. Multi-Agent Systems
21. ML Engineering — LoRA, quantization, MoE experiments

## Portfolio Structure (Phase 15 target)

rag-portfolio/
├── 01-naive-rag/
├── 02-advanced-rag/
├── 03-agentic-rag/
├── 04-evaluation-framework/
├── 05-production-platform/
└── shared/
