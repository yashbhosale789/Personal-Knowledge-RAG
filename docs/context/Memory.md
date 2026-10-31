# Personal Knowledge OS — Claude Project Memory
**Last consolidated:** 2026-10-29  
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
  - `rag-project/deploy.sh`: Production deployment script (ships in the image with prod config).
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
  - Deployment script `rag-project/deploy.sh` verifies image pull, starts container, runs health check, flushes Redis semantic cache, and executes a warm-up query before finalizing.
  - Rollback verified: tested rolling back to `.prev_image_tag` on container failure.
  - GitHub path filtering tested: markdown/docs pushes do not trigger unwanted Docker builds.
- Grafana made optional via Docker Compose profile; on-demand access via SSH tunnel without loading VM resources continuously.
- Do not reimplement or revisit completed deployment work without a specific bug or explicit request.

### Phase 13: LLMOps — CLOSED 2026-10-29 (started 2026-10-17). Phase 14 CLOSED 2026-10-30. Current phase: 15 (RAG pipeline hardening and scale)
 
Phase 13 is split into sub-chats **13.0–13.6**, one plan step per chat.
 
**Phase plan**
- **13.0 Evaluation foundation:** Grow validated golden dataset to roughly 50–60 questions spanning normal, difficult, ambiguous, multi-hop, unanswerable, and adversarial cases; synthetic questions must be validated by Yash. Add retrieval-relevance labels. Build a harness that compares two variants on the same questions and reports a confidence interval.
- **13.1 Token/cost accounting:** CLOSED 2026-10-26 as new-numbering 13.3 (see the 13.3 entry in §3), PR #72.
- **13.2 Prompt versioning:** CLOSED 2026-10-26 (see the 13.2 entry in §3). Prompts stay in `config.py`; `config.PROMPT_VERSION` (content hash) in every response/log/metric/cache namespace/eval record. No external prompt platform.
- **13.3 Reranker/model benchmark:** Compare candidates through evaluation harness. Retrieval metrics (Recall@K, MRR, NDCG) do not require LLM judge calls.
- **13.4 Tracing:** Add Langfuse tracing, fail-open and non-blocking. Langfuse Cloud Hobby proposed—confirm with Yash before taking this step and verify free-tier terms. Self-hosting impractical on current hardware.
- **13.5 Token optimization:** Each change validated against evaluation harness.
- **Human feedback endpoint:** delivered as Phase 14.0 (CLOSED 2026-10-30, PR #95); see the 14.0 entry in §2.
- **Operating constraints:** Hard $0 budget. Groq free-tier TPM limits apply. Evaluation runs must be batchable, resumable, and offline paired comparisons (no online traffic split).
 
**Phase 13.0 (Evaluation foundation) — close-out 2026-10-28; item 1 partly evidenced**
- Dataset `v1` = `51bcd1e330`, corpus `c1` = `9fc4650202` (`store.run_ids()`, written into every eval record beside the fingerprint). Test split (12) frozen.
- Judge calibration: n = 20 per metric (10 good / 10 bad), AUC 1.0 on all three metrics.
- 27 of 42 synthetic questions have no review record; labels unverified until spot-checked (owned by 15.1, before dataset v2).
- Failure analysis: `docs/architecture/eval-failure-analysis-2026-10-28.md` (saved `c83fff9ba7` answers + fresh retrieval run, $0).

**13.0a Status:**
- `eval/tools/validate_dataset.py` validates schema and evidence spans against `storage/chunks.json` using alphanumeric-only normalization. Exits 0 on `eval/data/golden_dataset.json` with Q01 in v2 format.
- Corpus rebuilt: 40 chunks across 5 PDFs in both Chroma and `storage/chunks.json`.

**Post-14 additions (2026-10-30, deployed with `7889f26`): chat memory (#100) and UI redesign (#107)**
- Optional `QueryRequest.history` (≤ 5 turns, answers clipped to 500 chars, untrusted). A follow-up is condensed into a standalone question (`condense_query`, `CONDENSE_SYSTEM`) before the cache and retrieval; on failure the raw follow-up skips the cache. No history = the old path, so eval and the `/query` response contract are unchanged. `CONDENSE_SYSTEM` is deliberately outside `PROMPT_VERSION`.
- Accepted exception to the 13/14 "no retrieval changes" rule; follow-up quality is unevaluated (no multi-turn eval questions) and adds one LLM call to time-to-first-token. Detail: roadmap "Post-14 additions".

**Phase 14.1 (React frontend) — CLOSED 2026-10-30; Phase 14 CLOSED the same day; next: Phase 15.0**
- PR 1 (UI on the existing `/query`): #97 (merge `d1821b0`), deployed by run `41027257170`, all CI green; browser round-trip verified on prod 2026-10-30 (row `6558d316-…`, `up`); unchanged after the PR 2 deploy. Decisions and design: roadmap §14.1. In short: `rag-project/frontend/` (Vite + React + TS, runtime deps react/react-dom only); built in the Dockerfile `web` stage and served by FastAPI at `/` and `/assets` only (`api/main.py` `mount_web`), so `deploy.sh`, compose and the Caddyfile are unchanged; key in `sessionStorage`; plain-text rendering plus a build-time CSP `<meta>`; advisory `Frontend` workflow; deploy smoke test checks `/` serves the UI.
- Mobile check by Yash 2026-10-30: fine.
- PR 2 (SSE `POST /query/stream`): #98 (merge `857f9a9`, deployed by run `41042230125`). CI: 288 passed / 6 strict xfail, coverage 76.89%; `/query` contract unchanged. Streams word by word through Caddy on prod. `token` events, then one `final` (`QueryStreamFinal` = QueryResponse fields + `caveat` + `chunks`), or one `error`; cache hit/abstain/empty send only `final`; fallback only before the first token. Contract snapshot `tests/contracts/query_stream_final.json` v1. The stream route sits outside the `/query` SLO rules and reports provider failures as 200 + `error` event (accepted; 15.4). Full detail: roadmap §14.1.

**Phase 14.0 (Human feedback endpoint) — CLOSED 2026-10-30; next: 14.1 React frontend**
- PR #95 (merge `2634d56`, deployed by run `41010543709`). CI: 276 passed / 6 strict xfail, coverage 75.46%; `/query` contract unchanged. Prod round-trip, replace-on-resubmit, 404 and survival of `--force-recreate` verified 2026-10-30; rows also survived a rollback to `0050465` and a redeploy of `2634d56` (deploy drill, same day). Full evidence: roadmap §14.0.
- **Design:** `/query` saves grounding to Redis `feedback:grounding:<request_id>` (24 h, cache hits too); `POST /feedback` {request_id, rating up/down, comment ≤1000, extra fields rejected} trusts only that grounding; SQLite `/app/feedback/feedback.db` on volume `rag_feedback_data`, one row per request ID (upsert); text nulled after 90 days; 30/min per key. Comments never go into prompts or logs. Feedback reaches eval only via `generate_candidates` / `review_candidates` with manual review.
- **Ops:** any `docker compose -f docker-compose.prod.yml` command on the server needs `export IMAGE_TAG="$(cat .image_tag)"` first (compose interpolates `${IMAGE_TAG:?}` for every command, `exec` included). The prod API key is not the local one; for prod checks run from the server with `KEY="$($C exec -T app printenv API_KEY)"`. Run `deploy.sh` by hand as `ubuntu`, never with `sudo`: root has no GHCR login, so the pull fails (`unauthorized`; the script then changes nothing). Rollback target: `.prev_image_tag`.

**Phase 13.5 (Operational readiness) — CLOSED 2026-10-29; Phase 13 CLOSED the same day**
- PRs #87, #88, #90, #92 (merge `81ed641`, deployed). CI on #92: 250 passed / 6 strict xfail, coverage 74.56%. Full evidence and open items: roadmap §13.5.
- **Authorization (F-19):** single-user system, one shared Bearer key; every key holder sees the whole corpus; one shared semantic cache. A second user needs per-user keys, a per-user cache namespace and retrieval-time document filtering first (`docs/templates/security/Security.md`).
- **Logging policy (F-21):** app logs keep at most 60 chars of query text and never secrets; container logs rotate 3 × 10 MB and are deleted on container recreation; Langfuse Hobby holds full text 30 days (deletion not guaranteed); semantic cache 24 h; Prometheus 30 days, no text; feedback comments (14.0) proposed 90 days (`docs/templates/security/Data_Privacy.md`).
- **SLOs (provisional until 15.4):** availability 99% non-5xx, latency 95% of `/query` within 10 s, 28-day window; recording rules `slo:query_errors:*` and `slo:query_slow:*` in `rag-project/prometheus-rules.yml`. Grafana alerting emails `ALERT_EMAIL` through Gmail SMTP (fast/slow burn for both SLOs, app down, provider failures, fallback rate). External uptime: `Uptime` workflow every 10 min.
- **Prod Grafana runs continuously** under `mem_limit: 256m`, with its dashboard, datasource and alerts provisioned from `rag-project/grafana/`; `deploy.sh` syncs those files and restarts Grafana if it is running. Its admin password lives in its own database volume (from 2026-10-12): `GF_SECURITY_ADMIN_PASSWORD` applies only on first start, so reset it with `grafana cli admin reset-admin-password` when they drift. Reach it with VS Code port forwarding or `aws ssm start-session ... AWS-StartPortForwardingSession` (needs the Session Manager plugin and a fresh `aws login`).
- **Limits:** app 1g, redis 192m (`maxmemory 64mb`, `volatile-lru`), prometheus 256m (30-day retention), caddy 128m, grafana 256m. Compose edits to services other than `app` and its dependency `redis` apply only on a manual `up` (needs `IMAGE_TAG`); recreating Redis drops the cache index, so run `create_cache_index()` afterwards. The first deploy of a new `deploy.sh` still runs the old one; its new synced files land on the next deploy.
- **Deploy key (F-18):** OIDC blocked by the AWS-managed project SCP (`iam:*Provider*`). Least-privilege `github-deploy` key, rotated 2026-10-29 with a rollback drill; next rotation 2027-01-27 (`docs/templates/security/Secrets_Management.md`).
- **Incident 2026-10-29:** keys committed in `postman/environments/` (commit `1bdfd19`) were auto-revoked when the repo went public; the Gemini verifier's 401 made every `/query` a 502. Fixes: new keys, nested Postman environments ignored, verifier degrades to a low-confidence uncached answer (`tier: verifier_error`).
- **Verifier on Groq qwen:** Gemini free tier took 18-24 s per call (two new projects); `config.CITATION_VERIFIER_MODEL` runs the verifier on Groq `qwen/qwen3.8-27b` (~1 s, different family from `gpt-oss-120b`, own rate limit) when `EVAL_PROVIDER=groq`. `EVAL_PROVIDER=gemini` restores Gemini. Answered queries are about 3-4 s end to end again.

## 3. Current evaluation and corpus facts
 
- `eval/` includes: `check_thresholds.py`, `ci_subset_dataset.json`, `eval_results.json`, `injection_cases.json`, `injection_eval.py`, `ragas_eval.py` (custom LLM judge, ~21 KB), `ragas_library_eval.py` (throwaway experiment, not used), `ragas_scores.json`, `run_eval.py`, `scanner_eval.py`, and `test_dataset.json`.
- The project uses a custom LLM-as-judge framework; RAGAS as a third-party library was abandoned due to dependency conflicts.
- Metrics judged: precision, recall, answer relevancy, faithfulness. Faithfulness measures grounding against retrieved context, not factual truth.
- Corpus PDFs (5 files, 40 total chunks): Adaptive Cruise Control (ACC - 9), Adjusting Seat Positions (8), Adjusting Steering Wheel (7), Advice for Pregnant Women (8), Aventro Motors How to Change a Tyre (8).
- Pipeline configuration: `CHUNK_SIZE=512`, `CHUNK_OVERLAP=64`; `TOP_K=5`; `RRF_K=60`; reranker `cross-encoder/ms-marco-MiniLM-L-6-v2`; `SUFFICIENCY_CE_FLOOR=-7.0`.
- LLM Providers: Groq primary (`openai/gpt-oss-120b` or Llama 3.3/3.1); OpenRouter and Gemini fallback; Ollama is local-dev-only.

**Phase 13.1 (new numbering — "Test foundation and CI hygiene") — CLOSED 2026-10-28.** Repo made public (`yashbhosale789/Personal-Knowledge-RAG`); branch protection on `main` requires `pytest` and `lint-security` (path-filtered build and eval gate deliberately not required). Original notes from 2026-10-23 follow; the "open exit criteria" bullet below is resolved.
- Suite in `rag-project/tests/` (`unit`, `api`, `integration`, `redis`, `slow`, `contracts`; live scripts moved to `tests/manual/`). Default run: **206 passed, 6 strict xfail, 3 deselected (`slow`)**, ~90 s, offline with an empty HF cache. Line coverage **65.55%**; CI floor `--cov-fail-under=65` (ratchet up only, never down). Measured over `src` and `api` (`.coveragerc`).
- Known defects pinned with `xfail(strict=True)`: F-01 (API-ingested docs not in BM25; deleted docs stay retrievable), F-03 (script ingest: not idempotent for shrinking docs, no injection scan, no cache clear), plus the buried soft-injection case (INJ04) the regex scanner misses. Phase 15.0 removes each marker as its fix lands.
- F-05: BM25 and the reranker are now lazy (`get_bm25()` / `get_reranker()` / `warmup()` in `advanced_rag.py`), warmed at app startup. Verified behaviour-preserving: all four stage outputs (dense/bm25/fused/reranked, scores rounded to 4 dp) were byte-identical for the 54 cached rewrites before and after. Side effect: the eval fingerprint changed because `src/pipeline` was edited, so older local `eval/runs/` entries no longer match.
- F-19: `verify_api_key` fails closed (401, never 500) when the key env var is unset or the presented key is non-ASCII. Startup already refused a missing/short key; both are now tested.
- F-06: `requirements.in` (direct deps) -> `requirements.txt` (pinned lock, py3.11/Linux, torch family excluded because torch is installed first from the CPU index); `requirements-dev.in/.txt` for tooling. `requirements-local.txt` now reads `requirements.in`.
- F-04/F-13: new workflows `tests.yml` (pytest + Redis service + dataset validation) and `audit.yml` (pip-audit, weekly); `eval-gate.yml` now runs on pipeline-path PRs, weekly and on demand, and reports (warning + job summary) instead of blocking when the run is incomplete (gate exit 2). `.github/dependabot.yml` covers pip and GitHub Actions.
- pip-audit currently reports 5 chromadb advisories (PYSEC-2026-311/3813/3814/3815): all concern the Chroma *server*; we use the embedded client; no fix version exists. Explicitly ignored in `audit.yml` — remove the ignores when chromadb ships a fix.
- **Open exit criteria (not verified):** (1) the new workflows have never run on GitHub — work is uncommitted by the owner's choice; push a branch, open a PR and confirm `Tests`, `Code Quality`, `Dependency Audit` are green before marking 13.1 closed. (2) Required checks: `gh api .../branches/main/protection` returns 403 ("Upgrade to GitHub Pro or make this repository public"), so branch protection cannot be enabled on this private free-plan repo; decide whether to upgrade/make public or rely on discipline. F-25 dead-code cleanup done in the touched files (`advanced_rag.py`, `main.py`, `auth.py`).

**Phase 13.2 (new numbering — "Prompt versioning") — CLOSED 2026-10-26**
- Merged as PR #67 (`49eb33f`), deployed the same day; old Redis index `semantic_cache_idx` dropped on prod after the deploy. CI: 222 passed / 6 strict xfail / 0 skipped (Redis tests ran), coverage 66.52% (floor 65), eval gate green.
- Prompts stay in `rag-project/config.py`; the generation user template moved there as `ANSWER_TEMPLATE`. `config.PROMPT_VERSION` = 12-hex SHA-256 of the five pipeline prompts (`REWRITE_SYSTEM`, `SYSTEM_PROMPT`, `ANSWER_TEMPLATE`, `SUFFICIENCY_JUDGE_SYSTEM`, `CITATION_VERIFIER_SYSTEM`); initial value `938331ced9a6`. Add any new pipeline prompt to that hash.
- Where it appears: `/query` response field `prompt_version` (API contract v2), `event=query` and `event=prompts_loaded` JSON logs, Prometheus `rag_prompt_info{version=...}`, the semantic-cache namespace (prompt version + answering model + verifier model; index `semantic_cache_idx_v2`, TAG filter on `namespace`), and eval generation/judge/retrieval records.
- Not covered: the judge/verifier `Question:/Context:` framings (in code; eval code hash only). F-14 entity guard unchanged (15.1).

**Phase 13.4 (Observability: request tracing) — CLOSED 2026-10-28**
- PRs #75–#79: request-ID correlation and per-stage timing, cache hits keep grounding, RAG quality signals, Langfuse tracing (fail-open, masked content), Grafana panels.
- Fail-open test: `tests/api/test_tracing.py::test_tracing_failures_never_fail_or_slow_a_query`.
- Panels verified on dev; prod Grafana stopped on purpose. Moving panels to prod is part of 13.5 alerting (decision pending: run prod Grafana with a memory limit vs alternatives).

**Phase 13.3 (new numbering — "Token and cost accounting") — CLOSED 2026-10-26**
- Merged as PR #72 (`0bb6fb6`), deployed by the same run. CI: 227 passed / 6 strict xfail, coverage 71.55% (floor 65); eval gate PASS (faithfulness 1.000, relevancy 0.902, 4 CI items); CI eval tokens/query mean 2844, p50 3657, 0/4 estimated (no `rewrite` stage in eval: cached rewrites).
- New `src/llm/usage.py`. `call_llm(..., stage=)` records `llm_tokens_total{stage,provider,model,type,source}` and `llm_call_duration_seconds{stage,provider,model}`. The four stages are `rewrite | sufficiency | generate | citation_verify`, and the default is `other`. `source` is `reported` (provider usage) or `estimated` (chars/4, only when the provider omits a count).
- `run_advanced_rag_pipeline` wraps its body in `usage.track()` (a ContextVar inside the one executor thread) and returns `llm_usage`. That value goes into the `event=query` log and eval generation records, and `generate.py` summary prints tokens per query. The API response contract is unchanged.
- Decision: under $0, cost means free-tier quota consumption (tokens and calls per provider/model), not a list price. Limits are recorded in roadmap §13.3 with the check date and are not hard-coded.
- Live sample on 2026-10-26 (corpus `c1`): about 3.2–3.4K tokens per answered query, about 1.2K per abstain; all counts provider-reported, including Gemini through its OpenAI-compatible endpoint. First local `/query` after merge: 12.97 s total, `llm_ms` 6.5 s (rewrite 2.3 s, verifier 2.3 s), two query-embedding passes ~3.5 s, ~3 s unaccounted. Retrieval timing is 13.4 step 2.
- Editing `src/pipeline` and `src/llm` changes the eval fingerprint, so local `eval/runs/` entries no longer match (CI deletes runs anyway).

## 4. Open issues and carryovers
 
### Security / repository hygiene
- **Postman environments:** nested `**/postman/environments/` and `*.postman_environment.json` are ignored (2026-10-29). Keys committed earlier in commit `1bdfd19` stay in git history; they were revoked and replaced, so treat that history as public. Postman's Native Git can stash uncommitted work when it switches branches: check `git stash list` if work disappears.
- `github-deploy` access key: rotate every 90 days; next 2027-01-27 (procedure in `Secrets_Management.md`).
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
- **LLMs:** Groq primary (`gpt-oss-120b`); OpenRouter & Gemini fallback; citation verifier on Groq `qwen/qwen3.8-27b` (13.5); Ollama local-dev-only.
- **Cache/Rate Limit:** Redis Stack (pinned by digest) with RediSearch vector KNN cosine distance; ephemeral by design, `maxmemory 64mb` with `volatile-lru` in prod.
- **Observability:** Prometheus metrics (`/metrics`), SLO recording rules, structured JSON logging. Grafana runs in prod under a 256m limit with provisioned dashboard and email alerts (13.5). Langfuse Cloud Hobby tracing (13.4). External uptime check from GitHub Actions.
- **Deployment:** Docker Compose on AWS EC2 (`t3.small`); Caddy automated TLS; GitHub Actions GHCR build & SSM Run Command auto-deploy.
- **CI:** GitHub Actions eval regression gate, Ruff linting, Bandit security scanning, CodeRabbit review.

## 6. Decisions and lessons that must guide future changes
 
### Explicitly rejected / deferred
- Do **not** propose changing the embedding model mid-project (`bge-m3`/NVIDIA rejected due to VRAM limits and re-indexing cost).
- No complex ABC/class inheritance hierarchy for LLM providers; prefer simple functional calls.
- Redis persistence is intentionally omitted; cache and rate limits fail open.
- $0 hard budget constraint: No paid services or unexpected cloud charges.
- Online A/B testing replaced with offline paired comparisons on the golden dataset.
- **Phase 15 scope trim (2026-10-31):** no storage migration now. 15.0 makes Chroma the single source of truth (BM25 rebuilt from it, reset on ingest/delete), and the store choice is deferred to the 15.1 measurements (next step SQLite FTS5 + `sqlite-vec`, then Postgres). **Corpus is PDF only, 100–150 files** (all file types would exceed 500 files in eight formats): no new loaders or format-specific chunking, F-15 closed by decision. The PDFs are public test data from another GitHub repo (not personal), so they may live in git and the image (check its license). 15.0 = PR 1 ingestion correctness (BM25 from Chroma, one shared ingest function, `force_reingest` removed, tokenizer left to 15.2) + PR 2 PDF upload/list/delete from the UI on prod (Chroma and documents on named volumes seeded from the image; new keyed `/documents` routes; path-based `/ingest` stays blocked at Caddy). Dropped: multi-format ingestion, reranker alternatives, long-context baseline, agentic vs deterministic, embedding-model experiment, L1/L3 caches, speculative generation (15.3 as a whole). Shrunk: 15.1 is index + measure the PDFs in one pass, F-14 guard, privacy, about 20–30 new eval questions; 15.4 is one k6 run at 5–10 users with provisional SLOs kept. Revisit only with measured evidence.
- Separate prompt files / a prompt registry with manual version strings (13.2): built, then rejected as ceremony for a single-developer repo. Prompts stay in `config.py`, versioned by content hash.
 
### Technical lessons
- All chunks and query embeddings must share the exact same embedding model and normalization.
- Grounding prompts must strictly enforce context-only boundaries, emit `[SOURCE N]` citations, and explicitly abstain on missing evidence.
- Semantic cache requires an entity guard in addition to the 0.87 cosine similarity threshold to prevent confusing semantically similar queries across different entities.
- Ollama requires native `/api/chat` with `stream: false`; its OpenAI-compatible endpoint allocates excessive KV cache.
- `create_cache_index()` must run on startup because fresh ephemeral Redis instances lack the RediSearch schema.
- A new field in the cache index needs a new index name (`create_cache_index()` returns early if the name exists); drop the old index afterwards **without** `DD`, because both indexes cover the `cache:` prefix.
- `rag-project/deploy.sh` deletes `cache:*` on every deploy, so prompt edits shipped by deploy were already invalidated in prod; the cache namespace matters for model scoping (`provider` override) and non-deploy restarts.
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
