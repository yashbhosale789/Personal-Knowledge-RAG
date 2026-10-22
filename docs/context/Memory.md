# Personal Knowledge OS — Claude Project Memory
**Last consolidated:** 2026-10-22  
**Purpose:** Persistent project context for Claude and AI engineering assistants. This file supersedes older memory notes where they conflict. Dates in the source notes are "last updated" dates for the corresponding entries.
 
## 1. Project identity and goals
 
- **Project:** Personal Knowledge OS / Personal Knowledge Base — production-oriented RAG portfolio project.
- **Owner:** Yash.
- **Goal:** Demonstrate practical, end-to-end AI engineering ability through a documented, phased system: ingestion, retrieval, grounded generation, evaluation, security/reliability, deployment, and LLMOps.
- **Active development copy:** `rag-project/` inside the repository. This is the only active application implementation.
- **Repository structure (Consolidated & Cleaned 2026-10-22):**
  - `rag-project/`: Core production application (FastAPI, hybrid retrieval, Chroma, Redis semantic cache, evaluation, tests, Docker).
  - `docs/`: Centralized documentation hub containing:
    - `docs/architecture/`: System context, architectural targets, and master roadmap.
    - `docs/runbooks/`: Operational runbooks (Redis Stack guide, etc.).
    - `docs/templates/`: 23 engineering specification templates (`development/`, `engineering/`, `operations/`, `security/`).
    - `docs/archive/`: Historical Word reports (`.docx`) and learning journals.
    - `docs/context/`: Core AI project context files (`Architecture.md`, `Roadmap.md`, `Memory.md`, `Ponytail.md`).
  - `prompts/`: Standardized AI collaboration workflows (`session-startup.md`, `session-memory-update.md`, `production-readiness-review.md`).
  - `deploy/`: Production deployment scripts (`deploy.sh`).
  - `postman/`: API test collections, environments, and Postman CLI specs.
  - `.github/workflows/`: CI/CD automation (`eval-gate.yml`, `code-review.yml`, `build-push.yml`).
  - *Historical Note:* Earlier standalone snapshot folders (`naive-rag/`, `advanced-rag/`, `agentic-rag/`, `rag-eval/`) were removed from the root to eliminate clutter and consolidate development.
- **Local environment:** Windows, VS Code, Python `.venv`, PowerShell/Git Bash, Postman.
- **Live demo:** Deployed with HTTPS via Caddy on AWS EC2. API uses Bearer token authorization; never put secret values or live access credentials in project memory.
- **Hard cost constraint:** $0 budget. Avoid recommendations that require paid plans or risk unexpected cloud charges.

## 2. Current status — highest priority
 
### Phase 11: Pre-deployment hardening — COMPLETE (2026-10-22)
- Full-codebase security and reliability review completed.
- `ruff` (linting) and `bandit` (static security analysis) added as required CI hard gates in `.github/workflows/code-review.yml`.
- `add_chunks` append-not-upsert idempotency bug fixed in `src/vectorstore/store.py` using SHA-256 deterministic IDs and deleting prior source chunks on re-ingestion.
- CI eval regression gate closed the abstention blind spot.

### Phase 12: Deployment — COMPLETE & CLOSED (2026-10-16 to 2026-10-22)
- Deployed to a 2 GB `t3.small` EC2 VM running Ubuntu. The `amazon-ssm-agent` is registered as an SSM managed node (`rag-demo`).
- Public endpoint security groups configured: HTTPS/443 open to `0.0.0.0/0`; SSH/22 strictly restricted to authorized admin IP (`/32`).
- Caddy automatically manages SSL certificates for the DuckDNS endpoint; public `/health` and protected `/query` endpoints verified live.
- Live performance: Three live `/query` calls measured ~3.5 s, 3.8 s, and 4.6 s. Memory used was ~890 MiB (~1.0 GiB available), swap ~416 MiB (app ~329 MiB, Redis ~83 MiB, Prometheus ~33 MiB, Caddy ~24 MiB). CPU peak ~28%.
- GitHub Actions auto-deploy to EC2 via AWS SSM Run Command is operational:
  - Custom SSM document `rag-deploy` restricts SHA parameter to 40 hex chars and executes zero-downtime updates.
  - Deployment script `deploy/deploy.sh` verifies image pull, starts container, runs health check, flushes Redis semantic cache, and executes a warm-up query before finalizing.
  - Rollback verified: tested rolling back to `.prev_image_tag` on container failure.
  - GitHub path filtering tested: markdown/docs pushes do not trigger unwanted Docker builds.
- Grafana made optional via Docker Compose profile; on-demand access via SSH tunnel without loading VM resources continuously.
- Do not reimplement or revisit completed deployment work without a specific bug or explicit request.

### Phase 13: LLMOps — CURRENT ACTIVE PHASE (started 2026-10-17)
 
Phase 13 is split into sub-chats **13.0–13.6**, one plan step per chat.
 
**Phase plan**
- **13.0 Evaluation foundation:** Grow validated golden dataset to roughly 50–60 questions spanning normal, difficult, ambiguous, multi-hop, unanswerable, and adversarial cases; synthetic questions must be validated by Yash. Add retrieval-relevance labels. Build a harness that compares two variants on the same questions and reports a confidence interval.
- **13.1 Token/cost accounting:** Account for tokens/cost by pipeline stage.
- **13.2 Prompt versioning:** Prompt files live in repository; include prompt version ID in every response/log/metric/cache namespace. No external prompt platform.
- **13.3 Reranker/model benchmark:** Compare candidates through evaluation harness. Retrieval metrics (Recall@K, MRR, NDCG) do not require LLM judge calls.
- **13.4 Tracing:** Add Langfuse tracing, fail-open and non-blocking. Langfuse Cloud Hobby proposed—confirm with Yash before taking this step and verify free-tier terms. Self-hosting impractical on current hardware.
- **13.5 Token optimization:** Each change validated against evaluation harness.
- **13.6 Human feedback endpoint:** Deferred to Phase 16 unless priorities change.
- **Operating constraints:** Hard $0 budget. Groq free-tier TPM limits apply. Evaluation runs must be batchable, resumable, and offline paired comparisons (no online traffic split).
 
**13.0a Status:**
- `eval/validate_dataset.py` validates schema and evidence spans against `storage/chunks.json` using alphanumeric-only normalization. Exits 0 on `eval/golden_dataset.json` with Q01 in v2 format.
- Corpus rebuilt: 40 chunks across 5 PDFs in both Chroma and `storage/chunks.json`.

## 3. Current evaluation and corpus facts
 
- `eval/` includes: `check_thresholds.py`, `ci_subset_dataset.json`, `eval_results.json`, `injection_cases.json`, `injection_eval.py`, `ragas_eval.py` (custom LLM judge, ~21 KB), `ragas_library_eval.py` (throwaway experiment, not used), `ragas_scores.json`, `run_eval.py`, `scanner_eval.py`, and `test_dataset.json`.
- The project uses a custom LLM-as-judge framework; RAGAS as a third-party library was abandoned due to dependency conflicts.
- Metrics judged: precision, recall, answer relevancy, faithfulness. Faithfulness measures grounding against retrieved context, not factual truth.
- Corpus PDFs (5 files, 40 total chunks): Adaptive Cruise Control (ACC - 9), Adjusting Seat Positions (8), Adjusting Steering Wheel (7), Advice for Pregnant Women (8), Aventro Motors How to Change a Tyre (8).
- Pipeline configuration: `CHUNK_SIZE=512`, `CHUNK_OVERLAP=64`; `TOP_K=5`; `RRF_K=60`; reranker `cross-encoder/ms-marco-MiniLM-L-6-v2`; `SUFFICIENCY_CE_FLOOR=-7.0`.
- LLM Providers: Groq primary (`openai/gpt-oss-120b` or Llama 3.3/3.1); OpenRouter and Gemini fallback; Ollama is local-dev-only.

## 4. Open issues and carryovers
 
### Security / repository hygiene
- **RESOLVED (2026-10-22):** Tracked Postman environments issue is resolved. `git ls-files postman/environments` confirmed clean (zero tracked files), and `postman/environments/` is ignored in root `.gitignore`.
- IAM access-key rotation reminder: Rotate `github-deploy` access keys approximately every 80–90 days.
- Confirm AWS account status and $0 constraint before modifying infrastructure.

### Deployment documentation & repository cleanup
- Root `README.md` and documentation hub (`docs/`) were created and restructured on 2026-10-22, reflecting the live AWS EC2 deployment, SSM workflow, and Phase 13 roadmap.
- `rag-project/README.md` remains focused on local subproject execution and can be kept in sync as needed.

### Potential quality/API issues to track during LLMOps
- Verify source numbering and source-list ordering if citation mismatches occur.
- Assess whether production request validation should explicitly reject `provider="ollama"` since Ollama is dev-only.
- Ensure provider is passed explicitly through `run_advanced_rag_pipeline` into `call_llm` to avoid mutating global `config.PIPELINE_PROVIDER` during concurrent requests.

## 5. Architecture and technology stack
 
- **API:** FastAPI + Uvicorn, Pydantic v2.
- **Embeddings:** `BAAI/bge-small-en-v1.5`, local via sentence-transformers (384-dim).
- **Vector store:** ChromaDB, SQLite persistence.
- **Keyword retrieval:** BM25 (`rank_bm25`).
- **Hybrid retrieval:** Dense + BM25 → Reciprocal Rank Fusion (RRF) → Cross-Encoder Reranker (`ms-marco-MiniLM-L-6-v2`).
- **LLMs:** Groq primary; OpenRouter & Gemini fallback; Ollama local-dev-only.
- **Cache/Rate Limit:** Redis Stack (`redis/redis-stack:latest`) with RediSearch vector KNN cosine distance; ephemeral by design.
- **Observability:** Prometheus metrics (`/metrics`) and structured JSON logging. Grafana profile on demand. Langfuse planned for Phase 13.
- **Deployment:** Docker Compose on AWS EC2 (`t3.small`); Caddy automated TLS; GitHub Actions GHCR build & SSM Run Command auto-deploy.
- **CI:** GitHub Actions eval regression gate, Ruff linting, Bandit security scanning, CodeRabbit review.

## 6. Decisions and lessons that must guide future changes
 
### Explicitly rejected / deferred
- Do **not** propose changing the embedding model mid-project (`bge-m3`/NVIDIA rejected due to VRAM limits and re-indexing cost).
- No complex ABC/class inheritance hierarchy for LLM providers; prefer simple functional calls.
- Redis persistence is intentionally omitted; cache and rate limits fail open.
- $0 hard budget constraint: No paid services or unexpected cloud charges.
- Online A/B testing replaced with offline paired comparisons on the golden dataset.
 
### Technical lessons
- All chunks and query embeddings must share the exact same embedding model and normalization.
- Grounding prompts must strictly enforce context-only boundaries, emit `[SOURCE N]` citations, and explicitly abstain on missing evidence.
- Semantic cache requires an entity guard in addition to the 0.87 cosine similarity threshold to prevent confusing semantically similar queries across different entities.
- Ollama requires native `/api/chat` with `stream: false`; its OpenAI-compatible endpoint allocates excessive KV cache.
- `create_cache_index()` must run on startup because fresh ephemeral Redis instances lack the RediSearch schema.
- Ingestion must use deterministic chunk IDs (SHA-256 of `source::chunk_index`) and delete previous source chunks only after successful validation.

## 7. Working style and collaboration rules
 
1. **Teach first, then implement.** Explain concepts and trade-offs before generating code.
2. **True line-by-line interleaving for code explanations:** Show a tiny snippet, explain it immediately, then proceed.
3. **Lazy senior developer discipline (`Ponytail.md`):** Write the minimum code that works. Avoid unrequested abstractions. Root causes over symptoms.
4. **Never assume codebase details.** Inspect source code, schemas, and configurations before proposing changes.
5. **Use Postman for API endpoint testing** as the primary interactive workflow.
6. **Windows Python invocation:** Use `python -m package.module` from project root.
7. **Keep major subtopics in dedicated chats.** Close each sub-chat with a clear summary and next-step prompt.
8. **Do not modify completed deployment or pipeline code** without explicit requirements.

## 8. Memory vs. Knowledge Graph (Graphify) Role Division
 
- **Graphify (`graphify-out/`):** Codebase structural knowledge graph. Automatically maps AST entities, function call hierarchies, dependency trees, community clusters, and blast-radius analysis across code files. Use for code navigation and refactoring.
- **`Memory.md`:** Architectural, operational, and conversational memory. Preserves human design rationale, rejected alternatives, operational budgets ($0 limit), AWS infrastructure nuances, security decisions, and cross-session continuity.
- **Synergy:** When Graphify is reinstalled, Graphify answers *"what code connects to what"*, while `Memory.md` answers *"why decisions were made"*. They complement each other with zero conflict.

## 9. Handy verification commands (PowerShell, from project root)
 
```powershell
# Verify total Chroma chunks
python -c "from src.vectorstore.store import get_vectorstore; print(get_vectorstore()._collection.count())"
 
# Verify chunks per source
python -c "from src.vectorstore.store import get_vectorstore; r = get_vectorstore().get(); from collections import Counter; print(Counter(m['source'] for m in r['metadatas']))"
 
# Verify zero tracked Postman environments (must return empty)
git ls-files postman/environments
 
# Run unit tests
python -m pytest
```
