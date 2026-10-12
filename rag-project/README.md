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
eval/                RAGAS, threshold, and prompt-injection evaluations
tests/               Unit and component tests
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
python test_setup.py
```

## Evaluation

The `eval/` directory contains the test datasets and evaluation runners. Most evaluation commands call an LLM and may incur provider latency or usage costs.

```powershell
python eval/run_eval.py
python eval/ragas_eval.py
python eval/check_thresholds.py
python eval/injection_eval.py
```

`run_eval.py` writes `eval/eval_results.json` and supports resuming completed cases. Set `EVAL_DATASET_PATH` to evaluate a different dataset. `check_thresholds.py` fails when the configured faithfulness or answer-relevancy floors are not met.

Run the automated tests with:

```powershell
python -m pytest
```

Some tests import embedding, vector-store, or LLM components and therefore may require the models, local data, Redis, and provider configuration to be available.

## Continuous Integration

Every pull request against `main` runs two required checks:

- **Eval Regression Gate** — rebuilds the index from `data/documents/`, runs the pipeline against a CI evaluation subset, and fails the PR if faithfulness or answer-relevancy drop below their configured floors.
- **Code Quality** — runs `ruff` (linting) and `bandit` (security static analysis) against the application code, excluding tests and dependencies. Both are hard gates: a finding fails the PR.

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
