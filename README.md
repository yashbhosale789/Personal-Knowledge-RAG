# Personal Knowledge OS — Production RAG System

[![Tests](https://github.com/yashbhosale789/Personal-Knowledge-RAG/actions/workflows/tests.yml/badge.svg)](https://github.com/yashbhosale789/Personal-Knowledge-RAG/actions/workflows/tests.yml)
[![Frontend](https://github.com/yashbhosale789/Personal-Knowledge-RAG/actions/workflows/frontend.yml/badge.svg)](https://github.com/yashbhosale789/Personal-Knowledge-RAG/actions/workflows/frontend.yml)
[![Uptime](https://github.com/yashbhosale789/Personal-Knowledge-RAG/actions/workflows/uptime.yml/badge.svg)](https://github.com/yashbhosale789/Personal-Knowledge-RAG/actions/workflows/uptime.yml)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

A single-user **Retrieval-Augmented Generation** system that answers questions about a personal document collection with grounded, cited answers, and abstains when the documents do not support an answer. It runs live on a 2 GiB AWS EC2 instance on a $0 budget, with CI/CD, an evaluation harness, tracing, SLOs and alerting.

The focus is engineering discipline around a RAG pipeline rather than model novelty: every quality claim is measured on a versioned dataset, every request can be traced end to end, and every known defect is pinned by a failing test until it is fixed.

**Live:** [yash-pkb-rag.duckdns.org](https://yash-pkb-rag.duckdns.org). The UI asks for the API key; this is a single-user system with one shared key, so the public link shows the UI but not answers.

<!-- TODO: add a short demo GIF of a question, a streamed answer with sources, and thumbs feedback. -->

**Status:** Phases 1–14 are closed (pipeline, deployment, LLMOps, feedback and React UI), as are 15.0 (one consistent ingest path, UI document upload) and 15.1 (the full corpus, offline). Phase 15.2 (retrieval tuning) is in progress. See [Known limitations](#known-limitations) and the [roadmap](docs/architecture/roadmap.md).

---

## Architecture

Four views: the whole system, the query pipeline, the ingestion pipeline, and delivery (CI/CD, deploy, eval gate, uptime).

### System overview

Everything runs on one EC2 instance in Docker Compose. Chroma, BM25 and both local models run inside the app process; only the LLMs, Langfuse and alert email are external.

```mermaid
flowchart LR
    subgraph Client ["Browser (React UI)"]
        UI["Chat: streamed answer, sources, thumbs feedback<br/>Documents: upload, list, delete PDFs"]
    end

    subgraph Host ["AWS EC2 t3.small · Docker Compose"]
        Caddy["Caddy (TLS)<br/>blocks /metrics and /ingest<br/>caps uploads at 11 MiB"]

        subgraph App ["FastAPI app (one uvicorn worker)"]
            Static["React build<br/>same origin, CSP"]
            QueryAPI["/query, /query/stream"]
            DocsAPI["/documents"]
            FeedbackAPI["/feedback"]
            HealthAPI["/health"]
            MetricsAPI["/metrics"]
            Models["In-process: bge-small-en-v1.5 embedder,<br/>MiniLM cross-encoder, BM25 index"]
        end

        Chroma[("Chroma<br/>volume chroma_data")]
        PDFs[("PDF files<br/>volume documents_data")]
        SQLite[("SQLite feedback<br/>volume feedback_data")]
        Redis[("Redis Stack<br/>semantic cache, rate limits,<br/>feedback grounding")]
        Prom["Prometheus<br/>SLO recording rules"]
        Graf["Grafana<br/>dashboards + alert rules"]
    end

    subgraph External ["External services"]
        LLM["LLM providers<br/>Groq → OpenRouter → Gemini"]
        Langfuse["Langfuse Cloud<br/>per-request traces"]
        Mail["Alert email (SMTP)"]
    end

    UI --> Caddy
    Caddy --> Static & QueryAPI & DocsAPI & FeedbackAPI & HealthAPI
    QueryAPI --> Models
    QueryAPI --> Chroma
    QueryAPI <--> Redis
    QueryAPI --> LLM
    QueryAPI -.-> Langfuse
    DocsAPI --> PDFs
    DocsAPI --> Chroma
    DocsAPI --> Redis
    FeedbackAPI --> SQLite
    FeedbackAPI --> Redis
    Prom -- "scrapes (internal)" --> MetricsAPI
    Prom --> Graf --> Mail
```

### Query pipeline

```mermaid
flowchart TD
    subgraph Client ["Browser (React UI)"]
        UI["Chat UI<br/>streamed answer, sources, thumbs feedback"]
    end

    subgraph Edge ["Caddy (TLS)"]
        Caddy["Reverse proxy"]
    end

    subgraph Query ["FastAPI: /query and /query/stream"]
        Auth["Bearer key + Redis rate limit"] --> Condense["Follow-up → standalone question<br/>(only with chat history)"]
        Condense --> Cache{"Semantic cache hit?<br/>RediSearch cosine ≥ 0.87"}
        Cache -- Yes --> Final["Answer + citations + request ID"]
        Cache -- No --> Rewrite["Query rewrite"]
        Rewrite --> Dense["Dense: Chroma<br/>bge-small-en-v1.5"]
        Rewrite --> Sparse["Sparse: BM25<br/>built from Chroma"]
        Dense & Sparse --> RRF["Reciprocal rank fusion"]
        RRF --> Rerank["Cross-encoder rerank<br/>ms-marco-MiniLM-L-6-v2, top 5"]
        Rerank --> Suff{"Sufficiency gate<br/>score floor + LLM judge"}
        Suff -- Insufficient --> Abstain["Abstain"]
        Suff -- Sufficient --> Gen["Grounded generation, streamed<br/>Groq gpt-oss-120b → OpenRouter → Gemini"]
        Gen --> Verify["Citation verifier<br/>Groq qwen3.8-27b"]
        Verify --> Conf["Confidence: high / low + caveat"]
        Conf --> Final
    end

    subgraph Stores ["State"]
        Redis[("Redis Stack<br/>cache, rate limits, feedback grounding")]
        SQLite[("SQLite on a named volume<br/>feedback")]
    end

    subgraph Telemetry ["Observability"]
        Prom["Prometheus<br/>SLO recording rules"] --> Graf["Grafana<br/>dashboards + burn-rate email alerts"]
        Langfuse["Langfuse Cloud<br/>per-request traces"]
    end

    UI --> Caddy --> Auth
    UI -- "POST /feedback" --> Caddy
    Caddy --> FeedbackRoute["FastAPI /feedback<br/>reads grounding from Redis"]
    FeedbackRoute --> SQLite
    FeedbackRoute -.-> Redis
    Auth <-.-> Redis
    Cache <-.-> Redis
    Final -.-> Prom
    Final -.-> Langfuse
```

### Ingestion pipeline

Since Phase 15.0 every write goes through one function, `ingest_file()` (`rag-project/src/ingestion/ingest.py`), so Chroma, BM25 and the cache cannot drift apart.

```mermaid
flowchart TD
    subgraph Entry ["Entry points"]
        Upload["UI upload: POST /documents<br/>bearer key, rate limit, .pdf name,<br/>%PDF- header, 10 MiB cap"]
        DevIngest["POST /ingest<br/>server path under data/documents/<br/>(local dev only, blocked at Caddy)"]
        Batch["scripts/ingest.py<br/>every PDF in data/documents/, sorted"]
    end

    Upload --> Lock{"Write lock free?<br/>one write at a time"}
    DevIngest --> Lock
    Lock -- No --> Busy["409: try again shortly"]
    Lock -- "Yes (upload)" --> Save["Save to documents_data volume<br/>same name: old file kept as backup"]
    Save --> Load
    Lock -- "Yes (/ingest)" --> Load
    Batch --> Load

    subgraph One ["ingest_file(): the one ingest path"]
        Load["Load + clean text<br/>PyPDFLoader, ligature and split-capital fixes"] --> HasText{"Text extracted,<br/>within size cap?"}
        HasText -- No --> Reject["Rejected before anything is deleted<br/>upload: old file restored"]
        HasText -- Yes --> Scan{"Prompt-injection scan"}
        Scan -- Flagged --> Reject
        Scan -- Clean --> Replace["Delete this source's old chunks"]
        Replace --> Chunk["Recursive character chunker<br/>512 characters, 64 overlap"]
        Chunk --> Embed["Embed: bge-small-en-v1.5, 384-d"]
        Embed --> Chroma[("Chroma<br/>collection personal_kb")]
    end

    Chroma --> Changed["index_changed()<br/>clear semantic cache, drop BM25 index"]
    Changed --> Rebuild["Next query rebuilds BM25 from Chroma"]
    Batch -.-> Snapshot["storage/chunks.json<br/>eval snapshot and corpus id"]

    DeleteDoc["DELETE /documents/name<br/>or DELETE /ingest"] --> DelChunks["Delete chunks, then the file"]
    DelChunks --> Changed
```

The loader also reads Markdown, DOCX and TXT, but the API and the batch script accept PDFs only. On first start in production, an empty `chroma_data` volume is seeded from the index built into the image; after that the volume is the source of truth.

### Delivery and operations

```mermaid
flowchart LR
    PR["Pull request"] --> CI["CI: pytest, ruff + bandit,<br/>pip-audit, CodeQL, frontend<br/>(lint, Vitest, Playwright)"]
    PR --> Gate["Eval regression gate<br/>LLM judge, 4 CI questions"]
    Weekly["Weekly schedule"] --> Gate
    CI --> Main["Merge to main"]
    Main --> Build["Build and Push Image<br/>UI build + Python app"]
    Build --> GHCR[("GHCR")]
    Build --> SSM["AWS Systems Manager<br/>no SSH port"]
    SSM --> Deploy["deploy.sh on EC2<br/>pull image, recreate app, wait healthy"]
    GHCR --> Deploy
    Deploy -- Healthy --> Warm["Clear semantic cache,<br/>warm-up query, smoke test"]
    Deploy -- Unhealthy --> Rollback["Redeploy previous image"]
    Uptime["Uptime workflow<br/>every 10 minutes"] --> Health["GET /health<br/>through Caddy"]
```

---

## What it does

**Retrieval and answer quality**
- Hybrid retrieval: dense (Chroma, `BAAI/bge-small-en-v1.5`) and BM25, merged with reciprocal rank fusion and reranked by a cross-encoder.
- A sufficiency gate (cross-encoder score floor, then an LLM judge) abstains before generation when the evidence is missing.
- Answers cite `[SOURCE N]`. A second model from a different family checks that each claim is supported; unsupported answers are marked low-confidence with a caveat.
- Chat memory: the UI sends the last five turns, and a follow-up ("what about the SUV?") is rewritten into a standalone question before the cache and retrieval see it.

**Serving**
- `/query` (JSON) and `/query/stream` (server-sent events: tokens, then one final event with verification, confidence and per-chunk sources).
- Provider retry and fallback (Groq → OpenRouter → Gemini; Ollama for local use). On the stream, fallback happens only before the first token.
- Redis semantic cache, namespaced by prompt version and model, so a prompt or model change never serves an old answer.
- `POST /feedback`: thumbs up/down and an optional comment, stored in SQLite with the prompt version, model, and the source, page and snippet of each chunk used (not just chunk IDs). Text is deleted after 90 days.

**Front end**
- React + TypeScript (Vite), served by FastAPI from the same origin as the API. Plain-text rendering and a Content-Security-Policy that allows only same-origin scripts and requests; the API key lives in `sessionStorage` only.

**Observability and operations**
- One request ID across the response, JSON logs, Prometheus metrics and the Langfuse trace.
- Per-stage latency and per-LLM-stage token accounting (`rewrite`, `sufficiency`, `generate`, `citation_verify`), marked reported or estimated.
- Provisional SLOs (99% non-5xx and 95% of `/query` within 10 s, over 28 days) with fast- and slow-burn alerts by email, plus app-down, provider-failure and fallback-rate alerts. All were fire-tested.
- External uptime check every 10 minutes from GitHub Actions.
- Container memory limits, Redis `maxmemory`, Docker log rotation, and a documented logging and retention policy.

**Security**
- Bearer key (fails closed), Redis rate limits, HTTPS via Caddy, `/metrics` and `/ingest` not reachable from the internet.
- Prompt-injection scanning on API ingestion; retrieved text, chat history and feedback comments are treated as untrusted.
- `bandit`, `ruff`, `pip-audit`, Dependabot and CodeQL in CI. One incident (committed keys, 2026-10-29) is written up in the roadmap, with its fixes.

---

## Evaluation

All numbers: corpus `c1` (5 PDF car manuals, 40 chunks), dataset `v1` (57 questions: 45 dev, 12 frozen test), prompt version `938331ced9a6`. The judge is calibrated against hand-labelled good and bad answers (n = 20 per metric, AUC 1.0 for faithfulness, correctness and relevancy).

**Retrieval** (37 answerable dev questions, no LLM calls):

| Stage | Recall@5 | MRR |
| --- | --- | --- |
| Dense | 0.946 | 0.769 |
| BM25 | 0.784 | 0.677 |
| Fused (RRF) | 0.932 | 0.741 |
| Reranked | 0.919 | **0.802** |

The reranker improves ranking (MRR) but not recall here, and on a 40-chunk corpus most differences are not statistically distinguishable. Re-measuring on the full corpus is Phase 15.1.

**End to end** (failure analysis, [report](docs/architecture/eval-failure-analysis-2026-10-28.md)): 34 of 45 dev questions are fully correct. All 8 questions that should abstain did abstain, so no answer was given without support. The largest failure group is over-abstention (4), then ranking (2), retrieval misses (2) and incomplete answers (2).

**CI gate:** an LLM-judge regression gate on 4 CI questions (faithfulness ≥ 0.85, relevancy ≥ 0.75) runs on pipeline changes and weekly. It reports rather than blocks when free-tier rate limits cut a run short.

Run it locally (from `rag-project/`):

```powershell
python -m eval.tools.validate_dataset      # dataset schema and evidence spans
python -m eval.harness.retrieval_eval      # retrieval metrics, no LLM calls
python -m eval.harness.generate            # answers for the golden dataset
python -m eval.harness.judge               # LLM-judge scores
python -m eval.harness.gate                # regression gate
python -m eval.security.injection_eval     # prompt-injection resistance
```

---

## Production deployment

- **Host:** one AWS EC2 `t3.small` (2 GiB) running Caddy, the app, Redis Stack, Prometheus and Grafana in Docker Compose, each with a memory limit.
- **CD:** a merge to `main` that touches the app builds the image (UI included), pushes it to GHCR, and runs `rag-project/deploy.sh` on the instance through AWS Systems Manager, so no SSH port is open.
- **Deploy script:** pulls the image, recreates only the app container and waits for it to be healthy, then clears the semantic cache and sends a warm-up query. If the new version is unhealthy, it redeploys the previous image automatically. Rollback has been drilled on production.
- **Secrets:** GitHub OIDC is blocked by the account's managed policy, so deploys use a least-privilege key rotated every 90 days.

---

## Known limitations

These are deliberate, tracked in the [roadmap](docs/architecture/roadmap.md), and each is pinned by a strict `xfail` test where it is a code defect:

- **Small corpus.** Production serves 5 PDFs (`c1`). The full corpus (100–150 PDFs) is indexed in Phase 15.1.
- **Single user.** One shared key; every key holder sees the whole corpus and shares one cache.
- **Provisional SLOs.** Single-user traffic is too sparse to tune them; no load test yet (Phase 15.4).
- **Free tiers.** Generation and verification both use Groq's free tier; the verifier degrades to a low-confidence, uncached answer if it fails.

---

## Local setup

**Prerequisites:** Python 3.11, Docker, Node 22 (only for UI development), and a Groq API key (or Ollama for fully local use).

```powershell
cd rag-project
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-local.txt -r requirements-dev.txt   # CUDA 12.4 torch; see requirements.in for CPU
```

Create `rag-project/.env`:

```dotenv
API_KEY=a-long-random-token
PIPELINE_PROVIDER=groq
GROQ_API_KEY=your-groq-api-key
EVAL_PROVIDER=groq
REDIS_HOST=localhost
REDIS_PORT=6379
```

Start Redis, build the index, and run the API:

```powershell
docker compose up -d redis
python scripts/ingest.py                         # documents in data/documents/
uvicorn api.main:app --reload --port 8000
```

UI development (proxies `/query` and `/feedback` to port 8000):

```powershell
cd frontend
npm ci
npm run dev
```

Tests: `pytest -m "not slow"` from `rag-project/` (offline, no model downloads).

---

## API

The query, feedback and ingest endpoints need `Authorization: Bearer <API_KEY>`.

**`POST /query`**

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "Where is the spare tyre on the Aventro Sedan?"}'
```

The response (schema pinned by `tests/contracts/query_response.json`) carries `query_id`, `answer`, `sources`, `rewritten_query`, `sufficiency`, `citation_check`, `confidence` (`high` / `low`), `outcome` (`answer`, `answer_low_confidence`, `abstain`, `empty`), `prompt_version` and `latency_ms`. An optional `history` (up to 5 earlier turns) makes the query a follow-up.

**`POST /query/stream`:** same body; server-sent `token` events, then one `final` event (`tests/contracts/query_stream_final.json`) or one `error`.

**`POST /feedback`:** `{"request_id": "...", "rating": "up" | "down", "comment": "optional"}`.

**`POST /documents`, `GET /documents`, `DELETE /documents/{name}`:** upload a PDF (multipart field `file`; a same-name upload replaces the old one), list the PDFs with their chunk counts, and delete one. Used by the UI; persisted on prod in named volumes (`docs/templates/operations/Backup_Recovery.md`).

**`POST /ingest`, `DELETE /ingest`:** take a server file path; local development only (blocked at Caddy).

**`GET /health`, `GET /metrics`:** health check and Prometheus metrics (`/metrics` is not exposed publicly).

---

## Repository layout

```text
rag-project/
├── api/                  FastAPI app: routers (query, stream, feedback, ingest, health), auth, middleware
├── src/                  Pipeline: ingestion, embedding, retrieval, llm (providers, cache, usage), pipeline stages
├── frontend/             React + TypeScript UI (Vite, Vitest, Playwright)
├── eval/                 Golden dataset, harness (retrieval, generate, judge, gate), security evals
├── tests/                Unit, API, contract, integration, Redis and slow suites
├── grafana/              Provisioned dashboard, datasource and alert rules
├── prometheus-rules.yml  SLO recording rules
├── docker-compose*.yml   Local and production stacks
├── deploy.sh             Deploy and rollback script (ships in the image)
└── Dockerfile            UI build stage + Python app
docs/                     Architecture, roadmap, runbooks, engineering and security docs
.github/workflows/        Tests, Code Quality, Dependency Audit, Frontend, Eval Regression Gate, Build and Push Image, Uptime
```

---

## Documentation

- [Roadmap and phase records](docs/architecture/roadmap.md): what was built, how it was verified, and the decisions behind it
- [Eval failure analysis](docs/architecture/eval-failure-analysis-2026-10-28.md)
- [System context](docs/architecture/system-context.md)
- [Documentation hub](docs/README.md) and [engineering templates](docs/templates/README.md)
- [Project memory](docs/context/Memory.md): durable decisions and lessons
- [Security policy](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

---

## License

Apache License 2.0. See [LICENSE](LICENSE).
