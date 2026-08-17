# RAG Project Roadmap

## Status
Phases 1–5 complete. Starting Phase 6.

## Phases 1–5 (Done)
1. Naive RAG — BGE embeddings, Chroma, OpenRouter
2. Advanced RAG — BM25 + dense, RRF, cross-encoder reranker, query rewriter
3. Evaluation — Custom LLM-as-judge, 12-question golden dataset, 4 metrics
4. Agentic RAG — Manual ReAct agent, LangGraph agent, metadata tool
5. FastAPI Backend — /query /ingest /health, async, retries, structured logging, provider fallback

## Phases 6–15 (Planned)
6. Ollama — Local LLM as fourth provider via config switch
7. Observability — Prometheus metrics, request tracing, context sufficiency, citation verification, confidence scoring, adversarial eval cases
8. Security + Reliability — Auth, Redis (rate limiting + semantic caching), prompt injection defense, input/output validation
9. Containerization + CI/CD — Dockerfile, docker-compose (app + Redis), GitHub Actions with eval regression gate
10. Deployment — Cloud VM, public URL, auto-deploy on merge
11. LLMOps — Prompt versioning, model benchmarking, A/B testing, token optimization, human feedback endpoint
12. Graph RAG — Entity extraction, knowledge graph (NetworkX → Neo4j), graph traversal retrieval
13. Multimodal RAG — Image/table extraction, vision embeddings, multimodal retrieval
14. Portfolio Extraction — Standalone sub-projects, shared/ library, benchmark comparisons, documentation
15. React Frontend — Streaming chat, citations, pipeline switcher, retrieval trace, human feedback UI

## Phases 16–20 (Future)
16. Kafka + EDA — Async ingestion pipeline
17. Kubernetes — Orchestration and scaling
18. MCP — Tool interoperability layer
19. Multi-Agent Systems
20. ML Engineering — LoRA, quantization, MoE experiments

## Portfolio Structure (Phase 14 target)
rag-portfolio/
├── 01-naive-rag/
├── 02-advanced-rag/
├── 03-agentic-rag/
├── 04-graph-rag/
├── 05-multimodal-rag/
├── 06-evaluation-framework/
├── 07-production-platform/
└── shared/