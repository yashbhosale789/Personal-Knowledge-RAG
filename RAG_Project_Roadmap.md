# RAG Project Roadmap

## Status
Phases 1–7 complete. Starting Phase 8.

## Phases 1–5 (Done)
1. Naive RAG — BGE embeddings, Chroma, OpenRouter
2. Advanced RAG — BM25 + dense, RRF, cross-encoder reranker, query rewriter
3. Evaluation — Custom LLM-as-judge, 12-question golden dataset, 4 metrics
4. Agentic RAG — Manual ReAct agent, LangGraph agent, metadata tool
5. FastAPI Backend — /query /ingest /health, async, retries, structured logging, provider fallback

## Phases 6–16 (Planned)
6. Ollama — Local LLM as fourth provider via config switch  [DONE]
7. Observability — Prometheus metrics, request/provider tracing  [DONE]
8. RAG Quality — Context sufficiency, citation verification, confidence scoring, adversarial eval cases
9. Security + Reliability — Auth, Redis (rate limiting + semantic caching), prompt injection defense, input/output validation
10. Containerization + CI/CD — Dockerfile, docker-compose (app + Redis + Prometheus/Grafana), GitHub Actions with eval regression gate
11. Deployment — Cloud VM, public URL, auto-deploy on merge
12. LLMOps — Prompt versioning, model benchmarking, A/B testing, token optimization, human feedback endpoint
13. Graph RAG — Entity extraction, knowledge graph (NetworkX → Neo4j), graph traversal retrieval
14. Multimodal RAG — Image/table extraction, vision embeddings, multimodal retrieval
15. Portfolio Extraction — Standalone sub-projects, shared/ library, benchmark comparisons, documentation
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
├── 04-graph-rag/
├── 05-multimodal-rag/
├── 06-evaluation-framework/
├── 07-production-platform/
└── shared/