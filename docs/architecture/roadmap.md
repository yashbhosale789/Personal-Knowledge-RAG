# Personal Knowledge OS — Detailed Roadmap (working plan)

Last reconciled: 2026-10-26

Current phase: **Phase 13 — LLMOps foundations**

Active development copy: `rag-project/`

Phase order from here: **13 → 14 → 15 → 16 → 17**. Later engineering tracks are learning-only (see the end).

Review behind this revision: `docs/architecture/review-findings-2026-10-23.md` (findings are cited below as F-nn).

## How to use this roadmap

- This file defines the planned sequence of work and the status of each phase.
- Use `Memory.md` for technical history, decisions, lessons, and open issues.
- Use `Architecture.md` for stable architecture and production-quality principles.
- Follow `Ponytail.md` for lazy senior developer discipline (YAGNI, root cause, shortest working diff).
- Follow `CLAUDE.md` for coding workflow and scope discipline.
- Treat statuses as verified only when supported by code, tests, logs, or explicit user confirmation. Do not mark work complete merely because it was discussed.
- Inspect the current repository before proposing code changes. If this roadmap conflicts with verified current code or newer confirmed decisions, flag the conflict and reconcile it rather than silently guessing.
- The clean, high-level roadmap is `docs/context/Roadmap.md`. This file is the detailed working plan: scope, exit criteria, deferred defects, interim rules and decisions. Keep the phase numbers in both files identical.
- Phase and sub-phase numbers are sequential and in execution order. Older notes (for example `Memory.md` §2) may use the previous numbering; see *Renumbering map*.

## Project goal

Build a production-oriented Personal Knowledge Base RAG system that demonstrates strong AI engineering and software engineering judgment: retrieval quality, grounded answers, evaluation, security, reliability, observability, deployment, and controlled operational improvement.

"Production-oriented" is judged against the *Production-readiness checklist* below, not by the number of phases completed.

## Hard constraints

- **Budget: $0.** No paid plans, no services that can bill unexpectedly. Before any infrastructure change, confirm the AWS account status and the instance's CPU-credit mode (T3 defaults to *unlimited*, which can bill surplus CPU).
- Groq free-tier TPM limits apply; verify current quotas and model availability when a decision depends on them.
- Hardware: single `t3.small` (2 GiB) in production; Windows dev machine.
- Embedding model stays `BAAI/bge-small-en-v1.5` unless a measured result justifies the re-index cost.

## Sequencing decision (2026-10-23)

The owner chose to **finish LLMOps (Phase 13), then build the feedback endpoint and frontend (Phase 14), and only then fix and scale the RAG pipeline (Phase 15)**, rather than interrupting the project mid-way for pipeline work. The cost of this choice:

- Known defects stay live in the pipeline until Phase 15, and every evaluation number produced in Phases 13 and 14 is measured on the 40-chunk corpus `c1`, where variants cannot be told apart (F-07). Both are tracked in *Known deferred defects* and *Interim rules* below.
- Because the frontend and feedback data are built against a pipeline that will change, Phase 13.1 adds API contract tests and Phase 14.0 stores feedback in a form that survives re-chunking and a storage change.

## Renumbering map

| Previous number | Now | Topic |
| --- | --- | --- |
| 13.7 | 13.1 | Test foundation and CI hygiene |
| 13.1 | 13.3 | Token and cost accounting |
| 13.9 | 13.5 | Operational readiness |
| 13.3 | 15.2 | Retrieval/model benchmarking and ablations |
| 13.5 | 15.3 | Token optimization |
| 13.6 / 16.1 | 14.0 | Human feedback endpoint |
| 16 / 16.2 | 14 / 14.1 | Frontend |
| 13.8 / 17.1 | 15.1 | Corpus scale-up |
| 17 | 15 | RAG pipeline hardening and scale |
| 14 | 16 | Graph RAG + Multimodal RAG |
| 15 | 17 | Portfolio extraction |

## Known deferred defects

These are real, verified by code reading (see the findings file), and **not** scheduled before Phase 15.

| ID | Defect | Risk while deferred | Interim mitigation | Fixed in |
| --- | --- | --- | --- | --- |
| F-01 | BM25 ignores API-ingested documents; deleted documents remain retrievable | Deleted content can still reach the LLM; new documents are invisible to keyword search | Do not use `/ingest` or `DELETE /ingest` in production | 15.0 |
| F-02 | Production index is baked into the image; API ingest/delete are not persisted | API changes vanish on deploy | Same as above; ingest only by rebuilding the image | 15.0 |
| F-03 | Script/Docker ingest skips injection scan, delete-before-add, cache clear | Stale chunks; unscanned documents | Corpus stays the 5 reviewed PDFs | 15.0 |
| F-09 / F-10 | Naive BM25 tokenizer; chunking never evaluated | Unknown retrieval-quality loss | None needed; measure in 15.2 | 15.0 / 15.2 |
| F-07 / F-08 | Corpus too small to discriminate variants; 12-question test split | LLMOps numbers on `c1` are provisional | Label every result `c1`; do not tune on the test split | 15.1 |
| F-14 | Cache entity guard hard-coded to `sedan/suv/hatchback` | Wrong cache hits on other domains | Single-domain corpus until 15.1 | 15.1 |
| F-15 | Loader handles 4 formats and the ingest API only `.pdf`; the target corpus has 8 formats | None at the current corpus | None | 15.1 |
| F-27 | Two separately maintained stores (Chroma and an in-memory BM25 built from `chunks.json`) are the root cause of F-01 | Same as F-01 | Same as F-01 | 15.0 |

## Interim rules (until Phase 15 closes)

- No `/ingest` or `DELETE /ingest` against production. The production corpus is the 5 PDFs baked into the image.
- The frontend (Phase 14) must **not** expose upload or delete.
- Every evaluation result quoted in Phases 13 and 14 states `corpus c1` and the dataset version.
- The 12-question test split stays frozen.
- Do not change retrieval, chunking, reranking or storage behaviour in Phases 13 and 14, except the behaviour-preserving refactor in 13.1 and the prompt-version/cache-key change in 13.2.

## Completed phases

### Phase 1 — Naive RAG

Complete. See project history and repository for implementation details.

### Phase 2 — Advanced RAG

Complete. Advanced retrieval and query-processing capabilities were introduced progressively.

### Phase 3 — Agentic RAG foundations

Complete as a learning milestone. It has not been compared with the non-agentic pipeline on the evaluation set (F-11); do not claim it improves anything until it is (Phase 15.2).

### Phases 4–6 — RAG improvements and local model/provider work

Complete. Includes the documented local Ollama integration and provider-handling decisions. Refer to the consolidated project memory for implementation specifics.

### Phase 7 — Prometheus observability

Complete for metrics collection. **No alert rules, SLOs, or load test exist** (F-20); alerting moves to Phase 13.5 and the load test to Phase 15.4. RAG quality metrics and detailed token/cost tracing are tracked in the LLMOps work.

### Phase 8 — RAG quality

Complete. Includes context sufficiency, citation verification, confidence/abstention behavior, and related quality work. Verify implementation in the repository before changing it.

### Phase 9 — Security and reliability

Complete. Includes Redis rate limiting and semantic caching, prompt-injection defenses, and request/response validation. Known gaps: injection scanning only runs on the API ingest path (F-03, Phase 15.0); auth edge case when the key env var is unset (F-19, Phase 13.1).

### Phase 10 — Containerization and CI/CD

Complete. Docker/Compose and the CI evaluation gate were verified. Grafana is optional and should not need to run continuously in production. Known gap: the corpus index is built inside `docker build` (F-02, Phase 15.0).

### Phase 11 — Pre-deployment hardening

**Complete, with two corrections (verified 2026-10-23).** `ruff` and `bandit` are CI hard gates; the CI eval gate's abstention blind spot is closed. Deterministic chunk IDs (SHA-256 of `source::chunk_index`) are in `store.py`, but the *delete-before-re-ingest* step lives only in the API router, not in `add_chunks`, so `scripts/ingest.py` is not idempotent for documents that shrink (F-03). Unit tests are not part of the CI gates (F-04, Phase 13.1).

### Phase 12 — Deployment

**Complete / closed (verified live on AWS EC2).**

Verified deployment work includes:

- AWS EC2 deployment using Docker Compose.
- Caddy reverse proxy providing automated HTTPS.
- GitHub Actions build/push and deployment workflow.
- AWS Systems Manager (SSM) Run Command automated deployment (`rag-deploy` document).
- Deployment script validation (`deploy/deploy.sh`), warm-up, pull-failure handling, and rollback drill tested.
- GitHub Actions path filtering (`rag-project/**`, workflow files) and optional Grafana profile.
- Deployment and rollback behavior verified live.

Do not reimplement or revisit completed deployment work without a specific bug, operational need, or user request. Scheduled operational needs: long-lived AWS keys (F-18, Phase 13.5), no container memory limits (F-16, Phase 13.5), index not persisted across deploys (F-02, Phase 15.0).

## Current phase

## Phase 13 — LLMOps foundations

Scope: evaluation close-out, tests and CI hygiene, prompt versioning, cost accounting, tracing, and operational readiness, all on the existing pipeline and corpus `c1`. **No retrieval, chunking, reranking or storage changes** (see *Interim rules*).

Sub-phases are numbered in execution order. Prefer one substantial sub-phase per conversation, then record verified results and open work before starting the next one.

| Step | Sub-phase | Why here |
| --- | --- | --- |
| 13.0 | Evaluation foundation — close-out | Finish what is nearly done; freeze `golden_dataset` v1 |
| 13.1 | Test foundation and CI hygiene | Tests protect everything that follows, including the frontend |
| 13.2 | Prompt versioning | Cheap; makes every later eval run reproducible |
| 13.3 | Token and cost accounting | Needed to reason about cost in Phase 15 |
| 13.4 | Observability: request tracing | Produces the request ID the feedback endpoint needs |
| 13.5 | Operational readiness | Alerting, secrets, limits, authorization decision |

### Phase 13.0 — Evaluation foundation (close-out)

**Status: substantially built per repo evidence (2026-10-23); formal closure pending.**

Repo evidence: `eval/data/golden_dataset.json` has 57 questions (normal 19, difficult 9, unanswerable 9, multi-hop 8, adversarial 7, ambiguous 5), `split` (45 dev / 12 test), `relevant` labels, `origin`, and a `ci` flag; `eval/harness/` has retrieval, generate, judge and gate modules; `eval/runs/compare_report.txt` reports paired differences with 98.3% confidence intervals; `eval/data/judge_calibration.json` exists. The earlier "Q01 v2 only" snapshot is obsolete.

Close-out checklist (each item must be verified, not assumed):

1. Confirm all 57 questions were manually validated (synthetic ones included) and mark which were not.
2. Record the judge's agreement with human labels from `judge_calibration.json` and state the sample size.
3. Declare the 12-question test split **frozen** and use it only for final reporting (F-08).
4. Run `eval/tools/validate_dataset.py` in CI (deterministic, no LLM).
5. Write the dataset version and a corpus identifier into every run's output so numbers are traceable.
6. Do a failure analysis: read every dev question the current pipeline gets wrong and bucket the causes (retrieval miss, ranking, generation, citation, wrong abstention). Keep the result; it drives Phase 15.

Exit: items 1–6 done; dataset tagged `v1` against corpus `c1` (the current 5 PDFs).

### Phase 13.1 — Test foundation and CI hygiene

**This sub-phase is about testing, not fixing.** It adds tests, CI automation and dependency hygiene. The pipeline and ingestion defects it uncovers (F-01, F-03) are *pinned with failing tests* here and *fixed* in Phase 15.0. The only code changes allowed are the behaviour-preserving refactor needed to make code testable (A) and the small safety fixes in (D).

Addresses F-04, F-05, F-06, F-13, F-19, F-22.

**Status: implemented locally 2026-10-23; NOT closed — exit criterion "CI green on a PR" unverified (uncommitted) and required checks cannot be enabled on this plan (branch-protection API returns 403).** Evidence: 206 passed / 6 strict xfail on the default run (offline, empty HF cache); coverage 65.55% with floor 65; ruff and bandit clean; retrieval output identical before/after the lazy-init refactor (54 queries, all stages); Redis layer verified against `redis/redis-stack-server`; slow smoke test passes with real models. Details and remaining manual step (required checks) are in `Memory.md` §2. F-22: `pip-audit` and Dependabot are in place; container-image scanning is not added (the roadmap scopes only pip-audit and Dependabot).

Method: write tests first. Known defects get `xfail(strict=True)` tests tagged with their finding ID. Phase 15.0 removes the markers as each fix lands; a strict xfail that starts passing fails the build, so nobody forgets.

#### A. Testability refactor (behaviour-preserving only)

- Remove import-time construction of BM25 and the reranker in `advanced_rag.py`: create lazily or inject, and load at app startup (F-05). The refactor must not change retrieval results; prove it with the existing retrieval baseline.

#### B. Test suite (pytest, $0, no network, no model downloads in the default run)

| Layer | What it covers | Notes |
| --- | --- | --- |
| Unit | chunker (the empty `test_chunker.py` exists), BM25 on a tiny fixture, RRF fusion, `confidence`, `json_reply`, citation verifier, `entity_mismatch`, injection scanner against `eval/data/injection_cases.json`, path validation (traversal, symlink, non-PDF), rate limiter, `call_with_fallback` with fake providers, eval-harness math (Recall@K, MRR, bootstrap CI, sign test) | Pure functions; milliseconds |
| API | `fastapi.testclient` with the LLM and retriever replaced by fakes: `/health`, `/query` 401/422/200 shape and abstention, `/ingest` and `DELETE` error mapping, auth with the key env var unset | Dependency overrides; no network |
| API contract | Pin the `/query` response schema (fields, types, citation structure) so Phase 15 changes cannot silently break the frontend | Schema snapshot test; changes require a deliberate version bump |
| Integration | Temp Chroma directory + deterministic fake embedder + real BM25: ingest → query → delete → query again. `xfail(strict=True)` regression tests for F-01 and F-03 | Default run, no model download |
| Redis | Semantic cache and rate limiter against `redis/redis-stack` | `@pytest.mark.redis`; runs in CI via a GitHub Actions `services:` container |
| Slow / model | Real embedder and reranker smoke test | `@pytest.mark.slow`; manual or scheduled, not per PR |

The integration layer touches the storage code that Phase 15.0 may replace. Keep those tests behind a small helper (ingest, query, delete) so they survive a storage change.

#### C. CI automation

- Add a `pytest` job (per PR, `-m "not slow"`) with pip caching, and `pytest-cov` with `--cov-fail-under` set to the first measured value, then raised as coverage grows (ratchet, never lowered). Make `pytest`, `ruff` and `bandit` required checks.
- Add `validate_dataset.py` and `pip-audit`; enable Dependabot for pip and GitHub Actions.
- Pin dependencies with a lockfile (`pip-compile` or `uv lock`) (F-06).
- Keep the LLM-judge eval gate, but run it on a schedule or on pipeline-path changes rather than every push, and report instead of blocking when the judge hits provider rate limits (F-13). Cheap deterministic checks block; expensive stochastic ones report.
- Optional: `pre-commit` running `ruff` and fast tests.

#### D. Small safety fixes allowed here

- Auth: fail at startup if the key env var is unset; return 401 not 500 (F-19).
- Delete dead commented code and fix log typos in files you touch anyway (F-25).

Exit: CI runs the suite on every PR and it is green; coverage floor recorded in `Memory.md`; F-01 and F-03 pinned by strict xfail tests; contract test in place.

### Phase 13.2 — Prompt versioning

**Status: CLOSED 2026-10-26.** PR #67 (merge `49eb33f`), deployed to production the same day; the old `semantic_cache_idx` was dropped after the deploy (runbook: `docs/runbooks/redis-stack-guide.md`).

Evidence: CI on PR #67 — `pytest` 222 passed / 6 strict xfail / 0 skipped (the Redis cache-invalidation tests ran against the `services:` container), coverage 66.52% (floor 65); `eval` gate, ruff and bandit green. Prompt text verified byte-identical before/after the move. Initial `PROMPT_VERSION`: `938331ced9a6`. No evaluation numbers are quoted for this sub-phase.

What was built: prompts stay in `rag-project/config.py` (the generation user template moved there as `ANSWER_TEMPLATE`). `config.PROMPT_VERSION` is a 12-hex hash of all five pipeline prompts, so any edit changes it. It appears in the `/query` response (`prompt_version`, contract v2), a structured `event=query` log line, the `event=prompts_loaded` startup log, the Prometheus `rag_prompt_info` metric, the semantic-cache namespace (prompt version + answering model + verifier model; index `semantic_cache_idx_v2`), and every generation, judge and retrieval-baseline eval record (prompts were already in the eval fingerprint).

Decisions:
- Separate prompt files with a registry and a manual version string were built, then rejected as ceremony for a single-developer repo: a content hash in `config.py` meets every exit criterion with less code.
- `deploy/deploy.sh` already deletes `cache:*` on every deploy, so in production a prompt edit was already invalidated by the deploy. The namespace's production value is model scoping (a `provider` override no longer receives another model's cached answer) and not depending on the deploy script (local runs, restarts, config changes).

Unresolved (not fixed by 13.2):
- The judge/verifier user-turn framings (`Question:/Context:`) stay in code: covered by the eval code hash, not by the cache namespace.
- F-14 (entity guard hard-coded to `sedan/suv/hatchback`) is unchanged; the namespace does not address it. Still owned by 15.1.

- Store prompts in the repository (`config.py`); the version is a hash of their text.
- Include the prompt-version identifier in relevant responses, logs, metrics, **and the semantic-cache key** (F-14), together with the model name.
- Record prompt versions in every eval run.
- Do not introduce an external prompt-management platform unless explicitly approved and justified.

Exit: changing a prompt changes the version, invalidates cache entries, and shows up in logs and eval output; one test proves each.

### Phase 13.3 — Token and cost accounting

Track token usage and estimated cost by pipeline stage where provider data permits. Keep missing/estimated usage clearly distinguished from provider-reported usage. Expose per-stage tokens and latency as Prometheus metrics and in structured logs. Report tokens per query in the eval output.

Exit: for a sample of queries, per-stage tokens and latency are visible; estimated vs reported usage is labeled.

**Status: CLOSED 2026-10-26.** Merged as PR #72 (`0bb6fb6`) and deployed by the same run (build and deploy jobs green). CI: 227 passed / 6 strict xfail, coverage 71.55% (floor 65); eval gate PASS (fingerprint `70a77e38f9`, 4 CI items: faithfulness 1.000, relevancy 0.902). The eval output now carries tokens per query: mean 2844, p50 3657, 0/4 estimated. Eval uses cached rewrites, so it has no `rewrite` stage.
- `call_llm(..., stage=)` keeps the provider usage block. OpenAI-compatible `usage.prompt_tokens/completion_tokens` is used for Groq, OpenRouter and Gemini; Ollama uses `prompt_eval_count/eval_count`. Any missing count is estimated (chars/4) and labelled `source="estimated"`.
- Prometheus metrics: `llm_tokens_total{stage,provider,model,type,source}` and `llm_call_duration_seconds{stage,provider,model}`. The pipeline result carries `llm_usage`, which goes into the `event=query` log and eval generation records. The eval summary prints tokens per query and the mean per stage.
- **Cost = free-tier quota consumption, not money.** Nothing is billed, and OpenRouter `:free` reports `cost: 0`. Limits were checked on 2026-10-26 and are not hard-coded, because they vary per account. Groq `gpt-oss-120b`: 30 RPM / 1K RPD / 8K TPM / 200K TPD. OpenRouter `:free`: 20 RPM / 50 RPD (1000 RPD after $10 of credits). Gemini: limits are per project and shown in AI Studio only.
- Live sample (corpus `c1`, Groq pipeline, Gemini verifier, all counts `reported`): Q01 2967+456 tokens, Q31 2650+515, Q12 (abstain) 948+239. An answered query uses about 3.2–3.4K tokens, so Groq's 8K TPM allows about 2 answered queries per minute. The rewrite stage uses about 100 completion tokens for a one-line rewrite (gpt-oss reasoning), which is a candidate for 15.3 token optimization.
- Not covered: retrieve/rerank timing (13.4). The per-query log covers only the successful pipeline attempt; Prometheus also counts calls made inside attempts that were retried.

### Phase 13.4 — Observability: request tracing

Starting point (2026-10-26): logs and metrics are in place. The request ID is created in `api/middleware/logging.py` and returned as `X-Request-ID` and `query_id`, but only the `api/` layer logs it; `src/` and `api/core/retry.py` do not. No spans or per-stage timing exist.

Order of work:

1. **Full correlation first (free, local):** store the request ID in a `contextvars` variable set by the middleware, and add a logging filter so every logger in `api/` and `src/` emits it without changing function signatures. Optionally accept a well-formed incoming `X-Request-ID`. Phase 14.0 depends on this request ID.
2. **Per-stage timing and outcome:** for the stages rewrite, retrieve, rerank, sufficiency, generate and citation verification, record duration, token counts, prompt version, provider, retry/fallback and outcome. Write these to structured JSON logs, and to Prometheus through a `stage` label.
3. **RAG quality metrics:** semantic-cache hits and misses, abstention / insufficient-context rate, citation-verification failures, empty retrievals.
   - **Cached answers must keep their grounding (fix first).** Today a cache hit returns `sources=[]`, `citation_check=None` and `confidence=None` (`api/routers/query.py`). This turns a cited answer into an uncited one, and would make cache hits look like quality failures in these metrics. Store sources, citation check, confidence and sufficiency with the cache entry, and return them on a hit. Add an API test, and update the response contract if any field changes.
   - Log the cache-hit similarity, and record whether the hit was an exact repeat. On a cache miss, log a hash of the rewritten query. Phase 15.3 uses these to decide on the exact-match (L1) and retrieval (L3) cache layers.
4. **External tracing — decided 2026-10-26: Langfuse Cloud Hobby (free plan), using the Langfuse Python SDK v3, which is built on OpenTelemetry.** Jaeger was rejected: another container, and no LLM-specific views. Self-hosting Langfuse was rejected: it needs Postgres, ClickHouse, Redis and S3, which don't fit on the 2 GiB `t3.small`.
   - Use the request ID as the trace ID, or record it in trace metadata, so one ID connects the response, logs and trace.
   - **Verify the current Hobby plan's limits and terms before implementation.**
   - Tracing is disabled when Langfuse keys are unset.
   - Add `opentelemetry-sdk` to `requirements.in` directly instead of relying on chromadb pulling it in. Pin it to the version already resolved in the lock file.
   - Privacy (F-21): mask retrieved chunk text and answers in traces by default. Send full content only after the Phase 15.1 privacy decision.
5. **Cardinality rules:** request IDs, query text, document and chunk IDs, and user input never become Prometheus labels; they belong in logs and traces. Metric labels use only values from a small, fixed set (route template, provider, stage, outcome).
6. Tracing must be non-blocking and fail-open: an observability outage must not break query serving. Use short flush timeouts. One test must prove it.

Exit: any `/query` can be followed by one request ID through the response, logs from every stage, metrics and its Langfuse trace. Per-stage and RAG quality metrics appear on the Grafana dashboard. The fail-open test passes.

### Phase 13.5 — Operational readiness

Addresses F-16 (limits), F-18, F-19 (authorization decision), F-20 (alerting), F-21 (logging policy).

- **SLOs (provisional):** define them from `c1` measurements and document them with a 28-day window and an error budget. Starting points:
  - availability: 99% of `/query` requests return a non-5xx response
  - latency: p95 of `/query` stays under a target set from measured p95

  Calculate both from the existing `http_requests_total` and `http_request_duration_seconds`, using Prometheus recording rules. Mark the targets provisional; they are finalised in Phase 15.4. Add an SLO / error-budget panel to the Grafana dashboard.
- **Alerts:** use Grafana alerting (already deployed), not a separate Alertmanager. Send notifications to a free channel (Telegram, Discord or email). Rules:
  - fast and slow error-budget burn rate for each SLO
  - health-check failures
  - LLM-provider failures and fallback rate
- **External uptime monitoring:** Prometheus runs on the same host, so it cannot report the host being down. Use a free external check on `/health`, such as UptimeRobot or a scheduled GitHub Actions workflow.
- **Docker log rotation:** add `json-file` rotation (`max-size`, `max-file`) to every service in `docker-compose.prod.yml`. Logs currently grow without limit on the instance disk.
- Pin the Prometheus and Grafana image versions in `docker-compose.yml`, which currently uses `latest`, to match prod.
- Replace long-lived AWS keys in GitHub Actions with GitHub OIDC to an IAM role (F-18); re-run the rollback drill afterwards.
- Add `mem_limit` to services and `maxmemory` to Redis in `docker-compose.prod.yml`, sized from current measurements (~0.9 GiB used on a 2 GiB host); confirm with a deploy and a warm-up query.
- Decide and document the **authorization model**: a single shared key is acceptable for a single-user system if stated as such; otherwise per-user keys with per-user cache and document filtering. If the system stays single-user, amend the "retrieve only authorized evidence" line in `Architecture.md`.
- Log retention and what is logged (queries can contain sensitive text); applies to feedback comments in Phase 14 as well.
- Document the rebuild procedure for the index from source documents. It will be revised in Phase 15.0 when ingestion changes.

Exit:
- Provisional SLOs are documented and shown in Grafana.
- A burn-rate alert and the external uptime check each fire in a test and reach the notification channel.
- Log rotation is active.
- The OIDC deploy works, and the container limits are active.
- The authorization and logging decisions are recorded in `Memory.md`.

### Closing Phase 13

Update the *Production-readiness checklist*. Every remaining gap must be owned by Phase 14 or 15. Provide the starting prompt for Phase 14.

### LLMOps operating constraints

- Budget target: $0 unless the user explicitly approves otherwise.
- A `/query` request can invoke multiple LLM stages, including rewriting, sufficiency judging, generation, and citation verification.
- Prefer offline paired comparisons over online A/B tests while there is insufficient production traffic to split.
- Evaluation runs must stay resumable/batchable; every run records dataset version, corpus identifier, prompt versions, model names and configuration.
- Do not assume old provider quotas or model availability remain current; verify them when the decision depends on them.

## Phase 14 — Human feedback and React frontend

Starts after Phase 13 closes. Delivered in this order.

### Phase 14.0 — Human feedback endpoint (backend first)

A minimal `POST /feedback`, authenticated like the other endpoints and rate limited.

- Fields: request ID (from Phase 13.4), rating, optional comment with a length cap. Comments are untrusted text: never put them into prompts automatically and render them as plain text.
- Store with each record: prompt version, model, and for each cited chunk the **source, page and a text snippet**, not just the chunk ID, because Phase 15 may re-chunk and change IDs.
- **Persistence:** the app container has no volume today (F-02). Store feedback in SQLite or JSONL on a **named volume** created for this purpose, so it survives deploys and rollbacks. This is a small compose change and does not touch the index. If Phase 15.0 selects Postgres, the feedback table migrates there; keep the schema simple so that migration is trivial.
- Retention period defined (Phase 13.5 logging policy).
- Feedback becomes candidate eval questions only through the existing `generate_candidates` / `review_candidates` flow with manual review. It is never auto-added to the golden dataset.
- Tests: validation, auth, persistence across container recreation, rate limit.

### Phase 14.1 — React frontend

Scope: query box, answer with citations, abstention display, and thumbs up/down plus comment calling `/feedback`. **No upload or delete UI** (*Interim rules*).

Decisions to record before building:

- **API key handling.** The API uses one shared Bearer key; a static single-page app cannot hold a secret. For a single-user system the default is that the user enters the key in the UI and it is kept in memory or `sessionStorage` only; never bake it into the build. Revisit only if the authorization model changes.
- **Hosting.** Preferred: build static files and serve them from the existing Caddy on the same origin (no CORS, no new service, negligible memory). Free static hosting is the alternative and requires CORS to be configured deliberately.
- **Rendering.** Treat answers, citations and source text as untrusted: render as text or sanitised markdown only (document content can contain markup).
- **Streaming (time-to-first-token).** `/query` returns only when the whole pipeline finishes, so the time to first token is the full latency. Add a streaming variant, for example SSE on a new route so the current `/query` contract stays unchanged. It streams generated tokens as they arrive, then sends citation verification, confidence, the caveat and the outcome as a final event. Cache hits are returned as a single event. Add contract tests for the stream format. The UI must handle an answer whose caveat or low-confidence flag arrives after the text.

Quality bar: ESLint and type-check clean, component tests (Vitest or equivalent), and a minimal end-to-end test against a mocked API; a CI job that lints, tests and builds; no new paid service. Keep the UI small: its value is a usable demo of the pipeline and the feedback loop.

Exit: usable on desktop and mobile widths, feedback round-trips and survives a deploy, CI green, `/query` contract tests still pass.

## Phase 15 — RAG pipeline hardening and scale

Starts after Phase 14 closes. This is where the deferred defects are fixed, the storage layer is decided, and the pipeline is measured on the real corpus. Production readiness is not claimed before this phase closes.

Guard rails: keep the `/query` response schema compatible with the frontend (contract tests from 13.1) or bump the version deliberately; the feedback store is independent of the index, so re-indexing does not touch it.

### Phase 15.0 — Storage decision and ingestion correctness

Fixes F-01, F-02, F-03, F-09, F-27 and removes the matching `xfail` markers.

**Why the storage question comes first.** F-01 exists because two stores are kept in step by hand: Chroma (on disk, in-process) and a BM25 index built in memory from `chunks.json`. Patching the sync would work, but choosing a store that holds vectors, keyword index and metadata together removes the failure class. The decision therefore precedes the fix.

Note on terms: Chroma is not "in-memory"; it persists to disk (SQLite and index files) but runs embedded in the app process, and its HNSW graph is loaded into RAM. What *is* purely in-memory is the BM25 index. The semantic cache in Redis is ephemeral by design.

#### Storage bake-off (time-boxed)

Run each shortlisted option on corpus `c1` and the Phase 15.1 Stage A subset, behind the same small retrieval seam (plain functions, no class hierarchy):

| Candidate | Why it is shortlisted | Main risk |
| --- | --- | --- |
| PostgreSQL + pgvector, self-hosted container | One transactional store for chunks, vectors, full-text search, feedback and eval metadata; ingest/delete in one transaction removes F-01 structurally; persistent volume; `pg_dump` backups; the common production choice | Native full-text ranking is not true BM25 (`ts_rank` lacks corpus-wide statistics), so hybrid quality must be measured; adds a container to a 2 GiB host |
| Qdrant, self-hosted container | Native dense + sparse hybrid with payload filtering; memory-efficient; persistent | Second system still needed for feedback and metadata; sparse-vector generation for BM25-style scoring must be built |
| SQLite with FTS5 + `sqlite-vec` | FTS5 provides real BM25; one file, transactional, no extra container; leanest memory | `sqlite-vec` search is brute force (no ANN), fine at tens of thousands of chunks, to be measured; single writer |
| Current Chroma + corrected BM25 sync (baseline) | Smallest change | Keeps two stores and the failure class behind F-01 |

Considered and **not shortlisted** (revisit only with evidence):

- **Pinecone.** Managed and zero RAM on the box, but: personal documents leave your infrastructure (F-21); a hosted dependency with free-tier quotas and terms that change; no native BM25 (sparse-dense hybrid needs a separate sparse model and index design); network latency added to every query; lock-in. Publicly reported Starter limits at the time of writing (third-party summaries, verify before relying on them): 2 GB storage, 1M read units and 2M write units per month, AWS us-east-1 only, indexes paused after about three weeks of inactivity, requests rejected with 429 once a cap is hit.
- **Managed free-tier Postgres (Supabase, Neon).** Same pgvector benefits without running it, but reported free limits are small (Supabase about 500 MB total database size and auto-pause after about a week of inactivity), data leaves your infrastructure, and a pause would take the demo down. A self-hosted container avoids all three.
- **Qdrant Cloud free tier.** Reported as one node with 1 GB RAM and 4 GB disk, suspended after a week of inactivity and deleted after four weeks. Unsuitable for an always-on service.
- **Elasticsearch/OpenSearch, Milvus, Weaviate.** Too heavy for a 2 GiB host shared with the app, Redis and Prometheus.

Measure for each candidate (same queries, same machine class): peak and steady RSS on a `t3.small`-equivalent limit, p50/p95 retrieval latency, ANN recall against exact search, retrieval metrics through the Phase 13.0 harness (Recall@K, MRR), ingest throughput, behaviour under concurrent ingest and query, restart and backup/restore, and implementation effort. Record the decision, the numbers and the rejected options in `Memory.md`. Expected outcome is Postgres + pgvector; the bake-off exists to prove it or overturn it, not to rubber-stamp it.

#### Then implement the chosen design

- One ingest/delete function used by the API, `scripts/ingest.py` and any build step: injection scan, delete-before-add, cache clear, and index update in one place.
- Index lifecycle: persistent storage on a **named volume** (or the database's own volume) and an **offline-built index**, replacing `RUN python scripts/ingest.py` in the Dockerfile. Build on the dev machine, not on the EC2 instance (CPU credits, live-traffic starvation). API ingest and delete then persist across deploys. Revise the rebuild procedure from 13.5.
- If the chosen store still needs a separate keyword index, add a startup consistency check (stored chunk count equals keyword-index count, otherwise fail fast).
- BM25 tokenizer: regex word tokens instead of `split()`; keep only if the harness shows it helps.
- Check whether the stored `source` string differs between the API and script paths (F-03).

Exit: decision recorded with numbers; strict xfails removed and passing; ingest through the API survives a deploy; the *Interim rules* about `/ingest` are lifted.

### Phase 15.1 — Corpus scale-up and multi-format ingestion

Addresses F-07, F-08, F-14, F-15, F-16, F-17, F-21.

The target corpus is about 1,190 files, ~25 MB, in eight formats: **PDF, DOCX, HTML, Markdown, CSV, XLS, XLSX, PPTX**. The current loader covers PDF, TXT, MD and DOCX; the API accepts only PDF.

#### Measure first

Count files and bytes per extension and sample a few of each. CSV and XLSX in particular can dominate the chunk count: 25 MB of tabular text is far more chunks than 25 MB of PDFs (see F-16).

#### Decisions (record in `Memory.md`)

1. **Per-format extraction.** Prefer small, single-purpose libraries (for example `python-docx`, `python-pptx`, `openpyxl`, `csv`/`pandas`, `beautifulsoup4` or `trafilatura`) over the heavy `unstructured` package on a 2 GiB image; decide by measuring image size and RSS. Legacy `.xls` needs its own reader (for example `xlrd`) or a conversion step.
2. **Structure-aware chunking.** The current recursive character splitter is wrong for tables. Spreadsheets and CSVs: chunk by groups of rows and repeat the header and sheet name in every chunk. Slides: one chunk per slide (title, body, and notes if notes are in scope). HTML: strip navigation/boilerplate first. DOCX: keep tables as tables, not run-on text. Metadata for every chunk: file type, page / sheet / slide, and row range where relevant.
3. **What is out of scope.** Retrieval over tables answers lookups ("what is the price of X"), not aggregations ("total sales in Q3"). Decide which question types the system supports, and make the unsupported ones abstain deliberately instead of guessing.
4. **Hidden and active content policy.** Hidden sheets, speaker notes, document comments, HTML comments and hidden elements, and formulas (read cached values, never evaluate): decide which are indexed. Whatever is extracted passes through the injection scanner, since hidden text is a classic injection carrier.
5. **Parser safety.** Office files are zip archives parsed from untrusted input: enforce file-size and decompressed-size limits, per-file timeouts, and never execute macros. Add these to the test suite with malformed and oversized samples.
6. **Privacy** (F-21): keep the personal corpus out of git and out of any public repo; decide what the public demo indexes.
7. **BM25 footprint** (if the chosen store still needs one): measure before choosing; options in order of effort are leaner tokenization and stop words, SQLite FTS5, a smaller corpus.
8. **Cache entity guard:** replace or confine the hard-coded `sedan/suv/hatchback` heuristic (F-14).
9. Align the ingest API with the loader so all eight formats are accepted, with a single allow-list shared by both.

#### Stages

- **Stage A (~100–150 files):** a representative subset covering all eight formats and some deliberately messy files. Build the index offline. Measure RSS, startup time, query p50/p95 and ingest time. Fix what breaks.
- **Stage B (full corpus):** only if Stage A projects within budget. Proposed budgets, to be confirmed against measurements: app steady RSS about 1.0 GiB or less including the chosen store, no sustained swap growth under 10 concurrent queries, startup within the compose `start_period`.

#### Evaluation after scaling (F-17)

- Keep the 5-PDF corpus `c1` as the CI corpus; CI never ingests the full set.
- Re-run retrieval-only baselines on the scaled corpus `c2` (no LLM calls needed).
- Re-audit every `unanswerable`, `adversarial` and `ambiguous` question against `c2`; new documents can make them answerable.
- Add questions for the new documents, including new categories for tabular lookups, slide content and HTML pages (target at least 100 in total, with a larger held-out test split), and record `dataset v2 / corpus c2`.
- Report `c1` and `c2` results side by side; do not overwrite `c1` history.

Exit: `c2` ingested through the production path in all eight formats, measurements recorded, dataset v2 validated, baselines filed.

### Phase 15.2 — Retrieval/model benchmarking and ablations

Use the harness on corpus `c2`. Retrieval metrics (Recall@K, MRR, NDCG) do not require LLM-as-judge calls. Each experiment is a paired comparison with confidence intervals:

1. **Chunking:** size (characters vs tokens), overlap, page-boundary merging (F-10), and the per-format strategies from 15.1.
2. **Retrieval variants:** dense, keyword (old vs new tokenizer), fused, reranked, reranker alternatives, `TOP_K` and candidate-pool size, on the chosen store.
3. **Stage ablations:** remove query rewriting, the sufficiency judge and citation verification one at a time; keep a stage only if it earns its latency, quota and quality (F-11). Also test skipping the rewrite only for short, unambiguous queries; this saves one LLM call from the time to first token.
4. **No-retrieval / long-context baseline** on `c1`, where the whole corpus fits in context.
5. **Agentic vs deterministic pipeline** (Phase 3) on the same questions.
6. **Embedding model:** only as a documented experiment; a change requires a full re-index.

Use the test split once, at the end. Exit: a written report stating which variants are distinguishable and which are not, with the chosen configuration and rationale.

### Phase 15.3 — Token and cache optimization

Evaluate each optimization against the 15.2 baseline. Report quality regressions as well as latency and cost improvements; do not trade answer quality for tokens without an explicit decision.

**Cache layering (decided 2026-10-26).** Constraint: no extra CPU load on the 2 GiB `t3.small`, and no additional services.

- **L1 — exact match. Build it only if the 13.4 logs show a meaningful share of exact repeats.**
  - Key: hash of `namespace | normalised query` (lower-case, trimmed, whitespace collapsed). Check it with a Redis `GET` before the semantic lookup.
  - A hit skips the query embedding and the vector search, so it saves CPU rather than adding load.
  - Use the same TTL as L2, and make `clear_cache()` remove both layers on ingest and delete.
- **L2 — semantic cache:** already in place (Phase 9).
- **L3 — retrieval cache. Build it only if the 13.4 logs show distinct queries being rewritten to the same text.**
  - Key: `namespace | rewritten query`. Value: the reranked chunk IDs.
  - A hit skips hybrid search and cross-encoder reranking, the main CPU cost.
  - `clear_cache()` must remove it on ingest and delete, and on the index rebuild from 15.0.
- **Connection reuse:** done 2026-10-26. `src/llm/client.py` keeps one pooled `requests.Session` for all providers, so the up to four LLM calls per `/query` skip a TCP + TLS handshake each.
- **Memory:** all layers stay in the existing Redis, under the 13.5 `maxmemory` with a `volatile-lru` eviction policy. No in-process cache, which would use memory the app needs on a 2 GiB host.
- **Rejected:**
  - Query-embedding cache: on a repeat, L1 already skips the embedding, and a paraphrase has to be embedded anyway.
  - Per-stage LLM-response cache (rewrite, sufficiency): it saves Groq tokens, not CPU or time-to-first-token, has a low hit rate beyond what L1 covers, and adds stale-answer risk.

  Revisit these only if 15.4 load testing shows a stage that caching would fix.

**Speculative generation (time-to-first-token).** Start answer generation in parallel with the sufficiency check, and discard the answer if the check abstains. This takes one LLM round-trip out of the time to first token. It costs no CPU, only Groq tokens spent on abstained queries. Decide on it from the 13.4 abstention rate, and confirm Groq free-tier token limits allow the extra usage.

### Phase 15.4 — Final operational validation

- Load test with a free tool (k6 or Locust) at the intended concurrency on the real instance; record p50/p95 and the failure point.
- Finalise SLO numbers and alert thresholds from measurements; re-check memory limits against `c2` and the chosen store.
- Run `prompts/workflows/production-readiness-review.md` and file the result.

Exit: the *Production-readiness checklist* has no open gaps, or each remaining one is accepted and recorded with a reason.

## Production-readiness checklist

Status as of 2026-10-23. Gap items name the owning phase.

| Area | Status | Owner / evidence |
| --- | --- | --- |
| Hybrid retrieval, reranking, grounded answers with citations, abstention | Done | Phases 2, 8 |
| Prompt-injection defense | Partial — API path only | F-03 → 15.0; multi-format → 15.1 |
| Auth (shared key), rate limiting, HTTPS | Done for single-user | Phases 9, 12; decision → 13.5 |
| Automated deployment, health check, rollback | Done, verified live | Phase 12 |
| Regression evaluation in CI | Partial — LLM-judge gate only | 13.0, 13.1 |
| Unit / API / integration tests in CI | Built in 13.1; confirm on the first PR run | F-04 → 13.1 |
| Reproducible builds (pinned dependencies) | Lock built in 13.1; confirm with a CI/Docker build | F-06 → 13.1 |
| Dependency / image vulnerability scanning | pip-audit + Dependabot built in 13.1; image scan still a gap | F-22 → 13.1 |
| Prompt / model versioning | Done — `config.PROMPT_VERSION` in responses, logs, metrics, cache namespace and eval records | 13.2, PR #67 |
| Per-stage cost and latency visibility | Partial — LLM stages done (tokens + latency, reported vs estimated); retrieval stages not timed | 13.3 PR #72, 13.4 |
| Request correlation and tracing | Partial — request ID in the `api/` layer only | 13.4 |
| Alerting and SLOs | **Gap** | F-20 → 13.5 (final numbers 15.4) |
| External uptime monitoring | **Gap** | 13.5 |
| Resource limits on containers | **Gap** | F-16 → 13.5 |
| Secrets without long-lived keys | **Gap** | F-18 → 13.5 |
| Logging / retention policy and log rotation | **Gap** | F-21 → 13.5 |
| User feedback loop | **Gap** | 14.0 |
| Usable front end | **Gap** | 14.1 |
| Storage architecture fit for production | **Gap, deferred** | F-27 → 15.0 |
| Ingestion correct and persistent | **Gap, deferred** | F-01, F-02, F-03 → 15.0 |
| Supports the real corpus formats | **Gap, deferred** | F-15 → 15.1 |
| Evaluation that can discriminate variants | **Gap, deferred** | F-07, F-08 → 15.1 |
| Corpus versioning and privacy decision | **Gap, deferred** | F-21 → 15.1 |
| Load test and capacity statement | **Gap, deferred** | F-16 → 15.4 |
| Backup / restore procedure | **Gap** | documented in 13.5, revised in 15.0 |

## Later roadmap — order: 16 → 17, after Phase 15

Introduce each only when it adds demonstrable value, and confirm scope before starting.

### Phase 16 — Graph RAG + Multimodal RAG

Planned as a **separate standalone project**, not built inside this repository. **Entry condition:** the Phase 15.2 failure analysis on the scaled corpus shows multi-hop or relationship failures that retrieval changes do not fix, or the corpus has material content in images or tables that text extraction loses. Without that evidence the phase is a technology exercise and should be labeled as one. Technologies (LangChain, LangGraph, LlamaIndex, Langfuse) are chosen from the actual requirements, not in advance.

### Phase 17 — Portfolio extraction

Organize selected work into portfolio-ready standalone artifacts and shared utilities only where justified. Preserve existing phase snapshots as standalone portfolio artifacts; do not casually modify them after snapshotting. Lightweight portfolio items — README accuracy, an architecture diagram, and a short write-up of the evaluation findings — are produced during Phases 13, 14 and 15, not deferred to this phase.

### Later engineering tracks — learning only

Kafka/event-driven ingestion, Kubernetes, MCP/tool integration, multi-agent systems, and ML/model-engineering experiments are **learning tracks, not part of the production path**. Rules:

- They live in separate branches or repositories and never gate Phases 13 to 17.
- Each needs a stated learning goal and a time box before it starts.
- $0: local or free-tier only (for example `kind`/`minikube`, local Kafka in Docker); never provision paid cloud resources for them.
- None changes the production deployment unless a measured problem in this system justifies it.

## Definition of phase completion

Before closing a subphase:

1. Verify the implementation in the repository.
2. Run relevant tests/evaluation checks and report their actual results; the test suite must be green in CI.
3. Record dataset version, corpus identifier and prompt versions for any evaluation numbers quoted.
4. Record important decisions and rejected alternatives.
5. List unresolved issues without implying they are fixed.
6. Update this roadmap's status, *Known deferred defects* and the *Production-readiness checklist*.
7. Update the consolidated project memory with concise, durable findings.
8. Provide a ready-to-use prompt for the next substantial subphase.
