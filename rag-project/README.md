# Personal Knowledge OS: RAG API

An experimental, production-oriented Retrieval-Augmented Generation (RAG) service for asking grounded questions about a personal document collection. The project combines local embeddings and retrieval with a configurable hosted or local LLM provider, and exposes the pipeline through a FastAPI API.

## What It Does

- Loads documents, splits them into overlapping chunks, embeds them with `BAAI/bge-small-en-v1.5`, and stores them in a local Chroma database.
- Rewrites a question before retrieval.
- Combines dense Chroma retrieval with BM25 sparse retrieval using reciprocal-rank fusion.
- Reranks candidates with `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- Rejects insufficient context before generation instead of guessing.
- Instructs the LLM to answer only from retrieved context and emit `[SOURCE N]` citations.
- Verifies citations and reports a confidence level and outcome.
- Scans API-ingested documents for prompt-injection patterns.
- Deletes ingested documents by source path, removing both the vector-store chunks and the underlying file.
- Provides Redis-backed semantic caching and Prometheus metrics.
- Deterministic per-chunk IDs ensure re-ingesting a document updates its existing chunks in place instead of duplicating them.

## Architecture

```text
Document -> loader -> chunker -> BGE embeddings -> Chroma
                                                   |
Question -> rewrite -> dense retrieval + BM25 -> RRF -> rerank
                                                   |
                              sufficiency gate -> grounded LLM answer
                                                   |
                         citation verification -> confidence and response
```

The main runtime entry point is `api.main:app`. The pipeline implementation is in `src/pipeline/advanced_rag.py`.

## Project Layout

```text
api/                 FastAPI application, routers, models, auth, middleware
src/embedding/       Local sentence-transformer embedding adapter
src/ingestion/       PDF, TXT, Markdown, and DOCX loaders plus chunking
src/llm/             Provider clients, retry/fallback, Redis cache, rate limiting
src/pipeline/        Advanced RAG stages and safety/quality gates
src/retrieval/       Dense retrieval, BM25, fusion, and reranking
src/vectorstore/     Persistent Chroma store
scripts/             CLI ingestion, querying, inspection, and agentic queries
eval/                Golden dataset, generate/judge/gate eval harness, retrieval and prompt-injection evaluations
tests/               Unit and component tests
frontend/            React + TypeScript web UI (Vite, Vitest, Playwright)
data/documents/      Default local document directory
storage/chroma/      Persistent vector database
storage/chunks.json  Human-readable CLI ingestion output
.github/workflows/   CI: eval regression gate, lint/security gate
```

## Requirements

- Python 3.11
- Git
- Redis Stack for semantic caching and rate limiting
- An LLM API key for the selected provider, unless using Ollama locally
- Enough disk space for the embedding and reranker models downloaded from Hugging Face
- NVIDIA GPU support is recommended for the current PyTorch CUDA 12.4 dependency, but the code can also be run with a compatible CPU-only environment after adjusting dependencies

## Local Setup

From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --extra-index-url https://download.pytorch.org/whl/cu124 -r requirements.txt
```

Create a `.env` file. Do not commit it. At minimum, configure the API authentication key and the key for the selected provider:

```dotenv
API_KEY=replace-with-a-long-random-value
PIPELINE_PROVIDER=groq
GROQ_API_KEY=replace-with-your-groq-key
EVAL_PROVIDER=groq
AGENT_PROVIDER=groq
REDIS_HOST=localhost
```

Supported pipeline providers are `groq`, `openrouter`, `gemini`, and `ollama`. Provider model names and API endpoints are currently configured in `config.py`. To generate a random API key:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Start Redis Stack separately if it is not already running:

```powershell
docker run -d --name redis-stack -p 6379:6379 -p 8001:8001 redis/redis-stack:latest
docker exec -it redis-stack redis-cli ping
```

## Ingest Documents

The CLI ingester recursively loads supported files from `data/documents/`:

```powershell
python scripts/ingest.py
```

## Run the API

```powershell
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

## Web UI

A small React app in `frontend/`: ask a question, read the answer with its `[SOURCE N]` markers, sources and an abstain or low-confidence banner, and rate it through `/feedback`. You type the API key into the page; it is kept in `sessionStorage` for that tab only, never in the build. Answers and sources are rendered as plain text, and the production build carries a Content-Security-Policy that allows only same-origin scripts and requests. There is no upload or delete UI (roadmap *Interim rules*).

In production the Dockerfile's `web` stage builds it (Node runs in CI only, never on the server) and FastAPI serves it at `/` and `/assets` on the same origin as the API, behind Caddy. Locally, with the API running on port 8000:

```powershell
cd frontend
npm ci
npm run dev          # http://localhost:5173, proxies /query and /feedback to :8000
npm run lint; npm run typecheck; npm test
npm run build; npm run e2e   # Playwright against the build, API mocked (once: npx playwright install chromium)
```

## API Reference

Protected endpoints require:

```text
Authorization: Bearer <API_KEY>
```

### Health

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

### Query

```powershell
$headers = @{ Authorization = "Bearer $env:API_KEY" }
$body = @{
 query = "What does the document say about vehicle maintenance?"
 provider = "groq"
 return_contexts = $true
} | ConvertTo-Json

Invoke-RestMethod `
 -Uri http://127.0.0.1:8000/query `
 -Method Post `
 -Headers $headers `
 -ContentType "application/json" `
 -Body $body
```

The response includes the answer, rewritten query, source filenames, number of chunks used, provider, latency, sufficiency verdict, citation check, confidence, and an outcome of `answer`, `answer_low_confidence`, `abstain`, or `cached`.

### Feedback

Rate an answer within 24 hours of the `/query` call, using its `query_id`:

```powershell
$body = @{ request_id = "<query_id>"; rating = "down"; comment = "Cited the wrong page." } | ConvertTo-Json

Invoke-RestMethod `
 -Uri http://127.0.0.1:8000/feedback `
 -Method Post `
 -Headers $headers `
 -ContentType "application/json" `
 -Body $body
```

`rating` is `up` or `down`; `comment` is optional (at most 1000 characters). Sending again for the same `request_id` replaces the rating and comment. The stored record takes the query, answer, model, prompt version and cited sources from what the server saved for that request, not from the client. Errors: `404` when the request ID is unknown or older than 24 hours, `429` above 30 requests a minute, `503` when Redis is down. Retention: `docs/templates/security/Data_Privacy.md`.

### Ingest a PDF

```powershell
$body = @{ file_path = "data/documents/manual.pdf"; force_reingest = $false } | ConvertTo-Json

Invoke-RestMethod `
 -Uri http://127.0.0.1:8000/ingest `
 -Method Post `
 -Headers $headers `
 -ContentType "application/json" `
 -Body $body
```

The API blocks documents that match configured prompt-injection patterns and clears the semantic cache after a successful ingest. Re-ingesting the same `file_path` replaces its existing chunks in place rather than duplicating them.

### Delete an ingested PDF

```powershell
Invoke-RestMethod `
 -Uri "http://127.0.0.1:8000/ingest?file_path=data/documents/manual.pdf" `
 -Method Delete `
 -Headers $headers
```

This removes matching Chroma chunks, deletes the file, and clears the semantic cache.

### Metrics

```powershell
Invoke-WebRequest http://127.0.0.1:8000/metrics
```

The endpoint returns Prometheus exposition data. The service also includes Redis and Grafana services in the Compose configuration.

LLM token and latency accounting (Phase 13.3), one series per pipeline stage (`rewrite`, `sufficiency`, `generate`, `citation_verify`):

- `llm_tokens_total{stage,provider,model,type,source}`: `type` is `prompt` or `completion`. `source="reported"` is the provider's own count. `source="estimated"` is a ~4 chars/token approximation, used only when the provider omits a count (for example, Ollama on a prompt KV-cache hit).
- `llm_call_duration_seconds{stage,provider,model}`: latency of each successful call. Its `_count` is the number of calls.

Under the $0 budget, "cost" means free-tier quota consumption, not money. For example, `sum by (provider, model) (increase(llm_tokens_total[1d]))` gives tokens per day, and `increase(llm_call_duration_seconds_count[1d])` gives requests per day. Compare these with the provider's daily limits; limits vary per account, so they are not hard-coded. Each `/query` `event=query` log line carries the same per-stage breakdown as `llm_usage`. Cache hits make no LLM calls and log `llm_usage: null`.

## CLI Querying

For a direct local pipeline query without starting FastAPI:

```powershell
python scripts/query.py
```

The script prompts for a question and prints the answer, sources, and number of chunks used. It sets `HF_HUB_OFFLINE=1`, so the required Hugging Face models must already be available locally.

Other useful scripts include:

```powershell
python scripts/advanced_query.py
python scripts/agentic_query.py
python scripts/inspect_embeddings.py
python tests/manual/check_setup.py
```

## Evaluation

The `eval/` directory contains the golden dataset and the evaluation runners. Run everything from `rag-project/` with `python -m`. Most evaluation commands call an LLM and may incur provider latency or usage costs. See `eval/README.md` for the full run order.

```powershell
python -m eval.tools.validate_dataset
python -m eval.harness.generate
python -m eval.harness.judge
python -m eval.harness.gate
python -m eval.security.injection_eval
```

`generate` and `judge` write to `eval/runs/` and resume completed cases. `gate` fails when the configured faithfulness or relevancy floors are not met. The earlier `run_eval`, `ragas_eval` and `check_thresholds` scripts are retired and kept untouched in `eval/legacy/`.

## Tests

Install the pinned dev tooling once (`requirements-dev.txt`), then run from `rag-project/`:

```powershell
pip install -r requirements-dev.txt
python -m pytest                      # default: unit, API, contract, integration — $0, no network, no model downloads
python -m pytest -m slow              # real embedder + reranker smoke test (downloads models on first run)
python -m pytest --cov                # with coverage (CI enforces a floor, see below)
```

| Layer | Location | Notes |
| --- | --- | --- |
| Unit | `tests/unit/` | pure functions, fake providers, eval-harness math |
| API + contract | `tests/api/` | `TestClient` with the pipeline faked; the `/query` response schema is pinned in `tests/contracts/query_response.json` |
| Integration | `tests/integration/` | temp Chroma + deterministic fake embedder + real BM25: ingest → query → delete → query |
| Redis | `tests/redis/` | `@pytest.mark.redis`; needs `redis/redis-stack` on `REDIS_HOST:6379`, skipped when none is reachable (a failure under `CI`) |
| Slow | `tests/slow/` | `@pytest.mark.slow`; excluded from the default run |

- Known defects are pinned by `xfail(strict=True)` tests tagged with their finding ID (F-01, F-03). Fixing one makes its test pass, which fails the build until the marker is removed.
- If the `/query` response shape changes on purpose, run `UPDATE_CONTRACT=1 python -m pytest tests/api/test_contract.py` and commit the snapshot (it bumps `contract_version`).
- `tests/manual/` holds live scripts (real LLM, real store). They are not collected by pytest.

## Dependencies

`requirements.in` lists the direct dependencies; `requirements.txt` is the pinned lock (Python 3.11, Linux) used by Docker and CI; `requirements-dev.in`/`.txt` hold the test tooling. torch is installed separately (CPU wheel in Docker/CI, CUDA via `requirements-local.txt`). To change a dependency, edit the `.in` file and recompile with the command in the header of the lock file.

## Continuous Integration

Pull requests against `main` run:

- **Tests** — `pytest -m "not slow"` with a Redis service container, offline with an empty Hugging Face cache (proves the default run never downloads a model), a coverage floor (`--cov-fail-under`, ratcheted up, never lowered), and `eval.tools.validate_dataset`. Required check: `pytest`.
- **Code Quality** — runs `ruff` (linting) and `bandit` (security static analysis) against the application code. Both are hard gates: a finding fails the PR.
- **Dependency Audit** — `pip-audit` on the locks, on dependency changes and weekly. Reports; it does not gate unrelated PRs.
- **Frontend** — ESLint, type check, Vitest component tests, build, and one Playwright end-to-end test against a mocked API at desktop and mobile viewports. Runs only when `frontend/` changes; advisory, not a required check.
- **Eval Regression Gate** — LLM-judged and rate-limit-prone, so it runs only when pipeline code, config, data or the eval harness change, weekly, and on demand. A real faithfulness/relevancy regression fails it; an incomplete run (provider rate limit) is reported as a warning and in the job summary instead of blocking.

Dependabot proposes weekly pip and GitHub Actions updates.

## Docker Compose

The Compose file defines:

- `app` on port `8000`
- Redis Stack on ports `6379` and `8001`
- Prometheus on port `9090`
- Grafana on port `3000`

Start the stack with:

```powershell
docker-compose up --build
```

The current Compose setup reserves an NVIDIA GPU for the app. Docker Desktop and NVIDIA Container Toolkit configuration may be required. The `app` service has no source volume mount, so code changes require `docker-compose up --build app` to take effect — there is no local hot-reload inside the container.

## Configuration Highlights

The main defaults in `config.py` are:

| Setting | Default |
| --- | --- |
| Embedding model | `BAAI/bge-small-en-v1.5` |
| Embedding dimension | `384` |
| Chunk size / overlap | `512` / `64` |
| Retrieval top-k | `5` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Chroma collection | `personal_kb` |
| Semantic cache threshold | `0.87` |
| Semantic cache TTL | `24 hours` |

Provider selection is controlled by `PIPELINE_PROVIDER`, while evaluation and agent providers are controlled independently by `EVAL_PROVIDER` and `AGENT_PROVIDER`.

## Security Notes

- Keep `.env`, API keys, and generated evaluation outputs out of version control where they contain sensitive data.
- Use a strong random `API_KEY`; the API expects it in a Bearer authorization header.
- API ingestion restricts paths to `data/documents/` and scans extracted text for prompt injection.
- Retrieved document text is treated as data in the generation prompt, but provider and model security still depend on the configured LLM service.
- The delete endpoint removes the source file as well as its vector-store chunks. Use it deliberately.
- CI enforces static-analysis security checks (`bandit`) on every pull request; findings block the merge rather than being discovered after deployment.

## Current Limitations

- The project is local-first: Chroma and downloaded Hugging Face models are stored on the machine running the service.
- The API and CLI use different ingestion format policies, as described above.
- Redis semantic caching is initialized lazily; query requests need a working Redis Stack instance.
- Provider fallback is useful for transient failures, but each provider still needs valid credentials and compatible model configuration.
- The health response currently emits the misspelled degraded status value `degraged` when the pipeline is not ready; clients should rely on `pipeline_ready` until that is corrected.
- No user-facing authentication/authorization layer exists yet beyond the single shared `API_KEY` — there is no per-user access control or document-level permissions.
- A full manual security and reliability review beyond automated linting is in progress (auth, tenant isolation, provider fallback logic, prompt-injection defenses).

## License

See [LICENSE](../LICENSE).
