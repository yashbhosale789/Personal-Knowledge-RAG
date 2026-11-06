# Development

Run the system locally, test it, and find your way around the tooling. Commands run from `rag-project/` unless noted.

**Contents:** [Setup](#setup) · [Run](#run) · [Web UI](#web-ui) · [Tests](#tests) · [CI](#continuous-integration) · [Dependencies](#dependencies) · [Docker Compose](#docker-compose) · [Scripts and tools](#scripts-and-tools)

---

## Setup

**Prerequisites:** Python 3.11, Docker, Node 22 (only for UI work), and a Groq API key (or Ollama for fully local use). Hugging Face models (embedder and reranker, a few hundred MB) download on first use.

```powershell
cd rag-project
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-local.txt -r requirements-dev.txt   # CUDA 12.4 torch; see requirements.in for CPU
```

Copy `.env.sample` to `.env` and fill it in. The minimum for local use:

```dotenv
API_KEY=a-long-random-token          # at least 16 characters
GROQ_API_KEY=your-groq-api-key
```

Optional: `OPENROUTER_API_KEY` and `GEMINI_API_KEY` (fallbacks), `HF_TOKEN`, the Langfuse keys, `EVAL_PROVIDER` (default `groq`) and `REDIS_HOST` (default `localhost`; the port is fixed at 6379).

Generate a key with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Never commit `.env`.

## Run

```powershell
docker compose up -d redis                       # Redis Stack (cache, rate limits)
python scripts/ingest.py                         # index data/documents/ (236 PDFs, about 4–8 min on CPU)
uvicorn api.main:app --reload --port 8000        # API at http://127.0.0.1:8000, docs at /docs
```

- **Tuning variants:** `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`, `RAG_CHUNK_MERGE_PAGES=1` and `RAG_TOP_K` select offline experiments (defaults 1024, 64, off, 3). A non-default chunking gets its own index (`storage/chroma_s<size>o<overlap>[m]`), so it never touches `storage/chroma`. Leave them unset in production.
- **Providers:** `PIPELINE_PROVIDER` (pipeline) and `AGENT_PROVIDER` (agentic scripts) are set in `config.py`, along with the model names; choices are `groq`, `openrouter`, `gemini` and `ollama`. `EVAL_PROVIDER` (judge and verifier) comes from `.env`. A `/query` request can override the pipeline provider with its `provider` field.

## Web UI

```powershell
cd frontend
npm ci
npm run dev                  # http://localhost:5173, proxies the API on :8000
npm run lint; npm run typecheck; npm test
npm run build; npm run e2e   # Playwright against the build, API mocked (once: npx playwright install chromium)
```

In production the Dockerfile's `web` stage builds the UI (Node never runs on the server), and FastAPI serves it at `/` on the same origin as the API.

## Tests

```powershell
python -m pytest -m "not slow"     # default: offline, no network, no model downloads
python -m pytest -m slow           # real embedder + reranker smoke test
python -m pytest --cov             # with coverage (CI enforces a floor)
```

| Layer | Location | Notes |
| --- | --- | --- |
| Unit | `tests/unit/` | pure functions, fake providers, eval-harness math |
| API + contract | `tests/api/`, `tests/contracts/` | `TestClient` with the pipeline faked; `/query` and stream schemas pinned |
| Integration | `tests/integration/` | temp Chroma, deterministic fake embedder, real BM25: ingest → query → delete → query |
| Redis | `tests/redis/` | needs `redis/redis-stack` on `REDIS_HOST:6379`; skipped locally when none is reachable, a failure in CI |
| Slow | `tests/slow/` | real models; excluded by default |
| Manual | `tests/manual/` | live scripts (real LLM, real store), not collected by pytest |

- Known defects are pinned by `xfail(strict=True)` tests tagged with their finding ID, so fixing one fails the build until the marker is removed.
- To change the `/query` response shape on purpose: `UPDATE_CONTRACT=1 python -m pytest tests/api/test_contract.py`, then commit the snapshot (it bumps `contract_version`).

## Continuous integration

| Workflow | Runs on | What it checks |
| --- | --- | --- |
| Tests (`tests.yml`) | every PR | `pytest -m "not slow"` with a Redis service, offline with an empty HF cache, coverage floor, `validate_dataset`. Required. |
| Code Quality (`code-review.yml`) | every PR | `ruff` and `bandit`; a finding fails the PR. Required. |
| Dependency Audit (`audit.yml`) | dependency changes, weekly | `pip-audit` on the lock files |
| Frontend (`frontend.yml`) | `frontend/` changes | ESLint, type check, Vitest, build, Playwright at desktop and mobile viewports |
| Eval Regression Gate (`eval-gate.yml`) | pipeline, config, data or eval changes; weekly; on demand | LLM-judge gate, see [EVALUATION.md](EVALUATION.md#ci-regression-gate) |
| Build and Push Image (`build-push.yml`) | merge to `main` touching the app | image build, GHCR push, deploy, smoke test, see [OPERATIONS.md](OPERATIONS.md#continuous-delivery) |
| Uptime (`uptime.yml`) | every 10 minutes | external `/health` check |

Also CodeQL and Dependabot (weekly pip and GitHub Actions updates). `main` requires `pytest` and `lint-security`; force pushes are blocked.

## Dependencies

`requirements.in` lists the direct dependencies; `requirements.txt` is the pinned lock (Python 3.11, Linux) used by Docker and CI; `requirements-dev.in` / `.txt` hold test tooling. torch is installed separately (CPU wheel in Docker and CI, CUDA through `requirements-local.txt`). To change a dependency, edit the `.in` file and recompile with the command in the lock file's header.

Optional: `pip install pre-commit && pre-commit install` runs the same `ruff` gate as CI on each commit.

## Docker Compose

`docker compose up --build` starts the app (`:8000`), Redis Stack (`:6379`, RedisInsight on `:8001`), Prometheus (`:9090`) and Grafana (`:3000`). The app has no source mount, so rebuild it (`docker compose up --build app`) after code changes. Production uses `docker-compose.prod.yml` through `deploy.sh`; see [OPERATIONS.md](OPERATIONS.md).

## Scripts and tools

| Command | Purpose |
| --- | --- |
| `python scripts/ingest.py` | index every PDF in the corpus folder through the shared ingest path |
| `python scripts/query.py` | one pipeline query from the terminal, no API (models must be cached: `HF_HUB_OFFLINE=1`) |
| `python scripts/advanced_query.py` | interactive queries against the full advanced pipeline |
| `python scripts/agentic_query.py` | the Phase 3 agentic RAG (ReAct / LangChain agents) |
| `python scripts/inspect_embeddings.py` | print the chunks stored in Chroma with their metadata |
| `python tests/manual/check_setup.py` | check the embedder, Chroma and that `.env` is loaded |
| `python experiments/semantic_cache_threshold.py` | the cache-threshold measurement |

**Elsewhere in the repo:**
- [`postman/`](postman/): Postman collections for Dev, QA and Prod, and a query suite by question type (golden set, sufficiency gate, citation verification, edge cases, semantic cache, document coverage).
- [`prompts/`](prompts/): AI-assistant workflow prompts (session start, memory update, production-readiness review, documentation setup and maintenance).
- [`docs/`](docs/README.md): roadmap, runbooks, and engineering, operations and security docs.

Contribution workflow: [CONTRIBUTING.md](CONTRIBUTING.md).
