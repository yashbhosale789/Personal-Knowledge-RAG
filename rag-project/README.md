# rag-project

The application: FastAPI API, RAG pipeline, React UI, evaluation harness, tests and deployment files. Project overview: [root README](../README.md).

| Folder | Contents |
| --- | --- |
| `api/` | FastAPI app: routers, models, auth, middleware |
| `src/` | Pipeline: ingestion, embedding, vector store, retrieval, LLM client and cache, pipeline stages, feedback, tracing |
| `frontend/` | React + TypeScript UI |
| `eval/` | Golden datasets, harness and tools ([eval/README.md](eval/README.md)) |
| `tests/` | Unit, API, contract, integration, Redis, slow and manual checks |
| `scripts/` | Batch ingest and CLI queries |
| `data/` | The corpus: 236 PDFs in `documents/` (MIT, with `SOURCE.md` and `SHA256SUMS`) |
| `grafana/`, `prometheus*.yml` | Dashboards, alert rules and SLO recording rules |
| `docker-compose*.yml`, `Dockerfile`, `Caddyfile`, `deploy.sh` | Local and production stacks |

- Set up, run and test: [DEVELOPMENT.md](../DEVELOPMENT.md)
- Endpoints: [API.md](../API.md)
- How it fits together: [ARCHITECTURE.md](../ARCHITECTURE.md)
- Deploy and operate: [OPERATIONS.md](../OPERATIONS.md)
- Evaluation: [EVALUATION.md](../EVALUATION.md)
