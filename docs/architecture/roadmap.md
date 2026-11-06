# Personal Knowledge OS — Detailed Roadmap (working plan)

Last reconciled: 2026-11-04

Current phase: **Phase 15 — RAG pipeline hardening and scale** (15.0 closed 2026-11-03, 15.1 closed 2026-11-04; next 15.2). Phases 13 and 14 closed 2026-10-29 and 2026-10-30.

Active development copy: `rag-project/`

Phase order from here: **15 → 16 → 17**. Later engineering tracks are learning-only (see the end).

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
| 14 / 16 | 16.3, 16.4 | Graph RAG + Multimodal RAG (merged into Phase 16, 2026-11-04) |
| 15 / 17 | 16 | Portfolio extraction → RAG portfolio and reusable eval kit |
| 18 | 17 | Multi-tenancy and RBAC |

## Known deferred defects

These are real, verified by code reading (see the findings file), and **not** scheduled before Phase 15.

| ID | Defect | Risk while deferred | Interim mitigation | Fixed in |
| --- | --- | --- | --- | --- |
| F-01 | BM25 ignores API-ingested documents; deleted documents remain retrievable | Deleted content can still reach the LLM; new documents are invisible to keyword search | Do not use `/ingest` or `DELETE /ingest` in production | **Fixed** 15.0 PR 1 (#115, 2026-11-02) |
| F-02 | Production index is baked into the image; API ingest/delete are not persisted | API changes vanish on deploy | Same as above; ingest only by rebuilding the image | **Fixed** 15.0 PR 2 (#123, 2026-11-02): index and documents in named volumes |
| F-03 | Script/Docker ingest skips injection scan, delete-before-add, cache clear | Stale chunks; unscanned documents | Corpus stays the 5 reviewed PDFs | **Fixed** 15.0 PR 1 (#115, 2026-11-02) |
| F-09 / F-10 | Naive BM25 tokenizer; chunking never evaluated | Unknown retrieval-quality loss | None needed; measure in 15.2 | **Measured** 15.2 PR 1 (2026-11-05, `c2`): F-09 `\w+` tokenizer not distinguishable after fusion and rerank, so `lower().split()` stays (closed by measurement). F-10: 1024/64 chunks are distinguishably better; chosen at `TOP_K` 3 for `c2`, not shipped to `c1`/prod yet (owner decision) |
| F-11 | No stage ablations and no no-retrieval baseline | Stages may not earn their latency and quota | None needed | **Measured** 15.2 (2026-11-06, `c2` dev n = 67): no ablation distinguishable. Rewrite and the sufficiency LLM tier earn nothing measurable; the owner decided 2026-11-06 to keep all stages (architecture unchanged). Closed by measurement and decision. No-retrieval baseline dropped 2026-10-31 |
| F-07 / F-08 | Corpus too small to discriminate variants; 12-question test split | LLMOps numbers on `c1` are provisional | Label every result `c1`; do not tune on the test split | **Addressed** 15.1 PR 2 (2026-11-04): corpus `c2` (2,221 chunks) and dataset `v2` (79 questions, 71 answerable); test split still 12 |
| F-14 | Cache entity guard hard-coded to `sedan/suv/hatchback` | Wrong cache hits on other domains | Single-domain corpus until 15.1 | **Fixed** 15.1 PR 1 (2026-11-04): a hit needs the same content words in the same order |
| F-15 | Loader handles 4 formats and the ingest API only `.pdf` | None: the corpus is PDF only (decided 2026-10-31) | None | Closed by decision |
| F-27 | Two separately maintained stores (Chroma and an in-memory BM25 built from `chunks.json`) are the root cause of F-01 | Same as F-01 | Same as F-01 | **Fixed** 15.0 PR 1 (#115, 2026-11-02): Chroma is the single source of truth |

## Interim rules (until Phase 15 closes)

- `/ingest` and `DELETE /ingest` stay blocked at Caddy (local development only). Production documents change only through `/documents` (upload, list, delete; 15.0 PR 2).
- Every evaluation result quoted in Phases 13 and 14 states `corpus c1` and the dataset version.
- The 12-question test split stays frozen.
- Do not change retrieval, chunking, reranking or storage behaviour in Phases 13 and 14, except the behaviour-preserving refactor in 13.1 and the prompt-version/cache-key change in 13.2.

## Completed phases

### Phase 1 — Naive RAG

Complete. See project history and repository for implementation details.

### Phase 2 — Advanced RAG

Complete. Advanced retrieval and query-processing capabilities were introduced progressively.

### Phase 3 — Agentic RAG foundations

Complete as a learning milestone. It has not been compared with the non-agentic pipeline on the evaluation set; that comparison was dropped from 15.2 on 2026-10-31, so do not claim it improves anything.

### Phases 4–6 — RAG improvements and local model/provider work

Complete. Includes the documented local Ollama integration and provider-handling decisions. Refer to the consolidated project memory for implementation specifics.

### Phase 7 — Prometheus observability

Complete for metrics collection. Alert rules and provisional SLOs were added in Phase 13.5 (F-20); the load test is Phase 15.4. RAG quality metrics and detailed token/cost tracing are tracked in the LLMOps work.

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
- Deployment script validation (`rag-project/deploy.sh`), warm-up, pull-failure handling, and rollback drill tested.
- GitHub Actions path filtering (`rag-project/**`, workflow files) and optional Grafana profile.
- Deployment and rollback behavior verified live.

Do not reimplement or revisit completed deployment work without a specific bug, operational need, or user request. Long-lived AWS keys (F-18) and container memory limits (F-16) were handled in Phase 13.5. Still scheduled: index not persisted across deploys (F-02, Phase 15.0).

## Phase 13 — LLMOps foundations (CLOSED 2026-10-29)

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

**Status: close-out done 2026-10-28 except item 1 (partly evidenced).** Dataset `v1` = id `51bcd1e330`, corpus `c1` = id `9fc4650202`.

- Item 1: 15 manual + 42 synthetic questions. `eval/runs/candidates_reviewed.jsonl` records 29 review decisions (15 accepted, 14 rejected), which covers 15 synthetic questions. **The other 27 synthetic questions have no review record**, and the owner does not recall how they were checked. Treat their labels as unverified until spot-checked; Q17's label is already suspect (see the failure analysis). Owner: 15.1, before dataset v2 is recorded.
- Item 2: judge `gemini-3.5-flash-lite`, `eval/data/judge_calibration.json`: 10 good + 10 bad answers per metric (n = 20 each). AUC 1.0 for faithfulness, correctness and relevancy, 0 failed calls. Mean score good/bad: faithfulness 0.82/0.00, correctness 1.00/0.00, relevancy 0.83/0.54. Relevancy separates least.
- Item 3: the 12-question test split is **frozen**: final reporting only, never for tuning. `eval/tools/assign_split` refuses to run once a test split exists.
- Item 4: `validate_dataset` runs in `tests.yml`.
- Item 5: every generation, judgment and retrieval record carries `dataset` and `corpus` ids (`store.run_ids()`: hash of the parsed JSON, so CRLF checkouts match CI). They sit beside the fingerprint, not in it, so adding a question does not invalidate stored runs.
- Item 6: `docs/architecture/eval-failure-analysis-2026-10-28.md`. 34/45 dev clean; largest bucket is over-abstention (5), then ranking (2), retrieval miss (2), incomplete generation (2), one label to review. No hallucinated answers on the 8 expected-abstain questions.

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

**Status: CLOSED 2026-10-28.** CI is green on every PR (Tests, Code Quality, Dependency Audit). The repo was made public (now `yashbhosale789/Personal-Knowledge-RAG`) so branch protection could be enabled: `main` requires `pytest` and `lint-security`, force pushes and deletion are blocked, admins can bypass. `Build and Push Image` and the eval gate are path-filtered and therefore not required (a skipped required check would block merges). Original implementation notes, 2026-10-23: Evidence: 206 passed / 6 strict xfail on the default run (offline, empty HF cache); coverage 65.55% with floor 65; ruff and bandit clean; retrieval output identical before/after the lazy-init refactor (54 queries, all stages); Redis layer verified against `redis/redis-stack-server`; slow smoke test passes with real models. Details and remaining manual step (required checks) are in `Memory.md` §2. F-22: `pip-audit` and Dependabot are in place; container-image scanning is not added (the roadmap scopes only pip-audit and Dependabot).

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
- `rag-project/deploy.sh` already deletes `cache:*` on every deploy, so in production a prompt edit was already invalidated by the deploy. The namespace's production value is model scoping (a `provider` override no longer receives another model's cached answer) and not depending on the deploy script (local runs, restarts, config changes).

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

**Status: CLOSED 2026-10-28** (confirmed by the owner). Delivered in PRs #75 (request-ID correlation, per-stage timing), #76 (cache hits keep their grounding), #77 (RAG quality signals), #78 (Langfuse tracing: fail-open, content masked by default) and #79 (Grafana panels for stage latency, LLM usage and RAG quality).

- Fail-open: `tests/api/test_tracing.py::test_tracing_failures_never_fail_or_slow_a_query` covers an exporter that raises, an SDK that raises and an unreachable Langfuse host; `/query` still returns 200 in under 1 s. Runs in the default CI suite.
- Grafana panels are verified on dev only. Production Grafana is stopped on purpose (on demand, 2 GiB host) and loads no dashboards from files; moving the panels to production goes with the 13.5 alerting work. Done in 13.5: prod Grafana runs under a 256m limit, with the dashboard and alert rules provisioned from files.

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

**Status: CLOSED 2026-10-29.** PRs #87 (verifier degrades instead of failing), #88 (uptime workflow), #90 (verifier on Groq qwen), #92 (limits, SLOs, Grafana alerting; merge `81ed641`, deployed). CI on #92: `pytest` 250 passed / 6 strict xfail, coverage 74.56% (floor 65); `lint-security` green. No evaluation numbers are quoted for this sub-phase.

Exit evidence:
- **SLOs documented and shown in Grafana:** availability 99% non-5xx and latency 95% within 10 s, both over 28 days (`docs/templates/engineering/Observability.md`). Recording rules in `rag-project/prometheus-rules.yml` (promtool unit tests pass; 10 rules loaded on prod). The prod dashboard has availability and latency SLO and budget panels.
- **Alerts fire and reach the channel:** Grafana email via Gmail SMTP to `ALERT_EMAIL`. Prod: the contact-point test email and a duplicated fast-burn rule both arrived quickly (2026-10-29); the copy was deleted, leaving the 7 provisioned rules. Locally (mailpit, fake exporter), the real availability and latency fast-burn, app-down, provider-failure and fallback rules fired and emailed at their real thresholds. External check: the `Uptime` workflow (`/health` every 10 min) failed against a bad URL and GitHub emailed the owner.
- **Log rotation:** `json-file` 3 × 10 MB on all five prod services.
- **Rotated key and rollback drill:** new `github-deploy` key; rollback to `275614f` (about 75 s) and forward to `9473d78`, both with the new key; old key deleted (2026-10-29, next rotation 2027-01-27).
- **Container limits active** (`docker inspect`, 2026-10-29): app 1g, redis 192m, prometheus 256m, caddy 128m, grafana 256m; Redis `maxmemory` 64 MB with `volatile-lru`. No OOM kills. After the manual `up`, a warm-up query took 10.5 s (the idle app had been swapped out while the other containers started), then 4.1 s for a new query and 2.0 s for a cache hit.
- **Decisions recorded in `Memory.md`:** authorization model and logging policy.

Decisions:
- F-18: GitHub OIDC is blocked by the AWS-managed project SCP. Kept the least-privilege key with 90-day rotation instead.
- F-19: single-user system, one shared API key, every key holder sees the whole corpus (`docs/templates/security/Security.md`; `Architecture.md` line amended).
- F-21: log policy in `docs/templates/security/Data_Privacy.md`. App logs keep at most 60 characters of query text; Langfuse holds full text for 30 days (deletion not guaranteed); the semantic cache holds it 24 h; Prometheus keeps 30 days with no text.
- Alerting: Grafana alerting with email, not a separate Alertmanager; uptime from a GitHub Actions cron, not UptimeRobot. Prod Grafana now runs continuously under its memory limit.
- The latency SLO uses a threshold (share of `/query` within 10 s) instead of a p95 estimate, read from the `le="10.0"` bucket (pinned by a test). Histogram buckets now reach 30 s so 15.4 can measure the true p95.
- Incident (2026-10-29): OpenRouter and Gemini keys committed in `postman/environments/` (commit `1bdfd19`) were auto-revoked when the repo went public, and the Gemini citation verifier's 401 turned every `/query` into a 502. Fixed by rotating the keys, ignoring nested Postman environments, and making the verifier degrade to a low-confidence, uncached answer (`tier: verifier_error`). GitHub secret-scanning alerts #1 and #2 resolved as revoked.
- The citation verifier moved from Gemini to Groq `qwen/qwen3.8-27b` (`config.CITATION_VERIFIER_MODEL`). Gemini's free tier took 18-24 s per call on two different new projects; qwen takes about 1 s, is a different model family from the generator `gpt-oss-120b`, and has its own Groq rate limit. `EVAL_PROVIDER=gemini` restores the Gemini verifier.

Unresolved (owned below or accepted):
- Generation and citation verification now both depend on Groq. A Groq outage already fails generation, and the verifier degrades safely. Revisit in 15.4.
- Grafana sits at its 256m limit (the excess is page cache; its own memory is about 176 MiB). Raise to 320m if it is ever OOM-killed; re-check all limits in 15.4.
- Starting several containers at once swaps the idle app out, so the next query is slow (10.5 s once). Normal deploys recreate only the app.
- The latency SLO also counts cache hits and abstentions, and single-user traffic makes both SLOs noisy; thresholds are final only in 15.4.
- Container image vulnerability scanning is still missing (15.4).
- The eval judge is still Gemini (13.0 calibration); with current Gemini latency, eval runs are slow. Re-check before 15.2.

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
- ~~Replace long-lived AWS keys in GitHub Actions with GitHub OIDC to an IAM role (F-18)~~: blocked by the AWS-managed project SCP (`iam:*Provider*` denied). Decided 2026-10-29: keep the least-privilege `github-deploy` key with 90-day rotation (`docs/templates/security/Secrets_Management.md`). Re-run the rollback drill after rotating.
- Add `mem_limit` to services and `maxmemory` to Redis in `docker-compose.prod.yml`, sized from current measurements (~0.9 GiB used on a 2 GiB host); confirm with a deploy and a warm-up query.
- Decide and document the **authorization model**: a single shared key is acceptable for a single-user system if stated as such; otherwise per-user keys with per-user cache and document filtering. If the system stays single-user, amend the "retrieve only authorized evidence" line in `Architecture.md`.
- Log retention and what is logged (queries can contain sensitive text); applies to feedback comments in Phase 14 as well.
- Document the rebuild procedure for the index from source documents. It will be revised in Phase 15.0 when ingestion changes.

Exit:
- Provisional SLOs are documented and shown in Grafana.
- A burn-rate alert and the external uptime check each fire in a test and reach the notification channel.
- Log rotation is active.
- The deploy works with the rotated key and the rollback drill passes, and the container limits are active.
- The authorization and logging decisions are recorded in `Memory.md`.

### Closing Phase 13

Update the *Production-readiness checklist*. Every remaining gap must be owned by Phase 14 or 15. Provide the starting prompt for Phase 14.

**Done 2026-10-29:** checklist updated below; every open row is owned by 14.0, 14.1 or a 15.x sub-phase, or accepted with a reason. The Phase 14 starting prompt was given at close-out.

### LLMOps operating constraints

- Budget target: $0 unless the user explicitly approves otherwise.
- A `/query` request can invoke multiple LLM stages, including rewriting, sufficiency judging, generation, and citation verification.
- Prefer offline paired comparisons over online A/B tests while there is insufficient production traffic to split.
- Evaluation runs must stay resumable/batchable; every run records dataset version, corpus identifier, prompt versions, model names and configuration.
- Do not assume old provider quotas or model availability remain current; verify them when the decision depends on them.

## Phase 14 — Human feedback and React frontend (CLOSED 2026-10-30)

Starts after Phase 13 closes. Delivered in this order.

### Phase 14.0 — Human feedback endpoint (backend first)

**Status: CLOSED 2026-10-30.** PR #95 (merge `2634d56`), deployed by run `41010543709` (build and deploy green; deploy created volume `rag_feedback_data`). CI on #95: `pytest` 276 passed / 6 strict xfail, coverage 75.46% (floor 65); `lint-security` green; `/query` contract unchanged (no version bump). No evaluation numbers are quoted for this sub-phase. Prod evidence (2026-10-30, through Caddy): `/query` → `POST /feedback` 200 `recorded`; resubmit replaced the rating and cleared the comment; unknown ID 404; the row (outcome `cached`, model `openai/gpt-oss-120b`) was identical after `up -d --force-recreate app`. Deploy and rollback drill (2026-10-30, `deploy.sh` as `ubuntu`): rolled back to the pre-14.0 image `0050465` (app recreated, compose synced, no volume mounted, warm-up 200), then redeployed `2634d56` (app recreated, `rag_feedback_data` mounted again, warm-up 200); both feedback rows were unchanged. A same-image re-run of the workflow (run `41019137706`) does not recreate the app, so it proves nothing here.

As built: `/query` saves grounding (query, answer, outcome, prompt version, model, and per chunk handed to generation its source, page, 200-char snippet and a `cited` flag) in Redis at `feedback:grounding:<request_id>` for 24 h, on cache hits too. `POST /feedback` takes only `request_id`, `rating` (`up`/`down`) and an optional comment (≤1000 chars, unknown fields rejected), reads the grounding (404 when gone, 503 when Redis is down) and upserts one SQLite row per request ID at `/app/feedback/feedback.db` on the `feedback_data` volume. Query, answer and comment text are nulled 90 days after the first rating (purge at startup and on every write). Rate limit 30/min per key. Code: `src/feedback.py`, `api/routers/feedback.py`. Retention: `Data_Privacy.md`. Note: grounding shares Redis's 64 MB `volatile-lru` budget, so it can be evicted before 24 h (feedback then returns 404). Adding `chunks` to the pipeline result changed the eval fingerprint (retrieval and generation unchanged).

A minimal `POST /feedback`, authenticated like the other endpoints and rate limited.

- Fields: request ID (from Phase 13.4), rating, optional comment with a length cap. Comments are untrusted text: never put them into prompts automatically and render them as plain text.
- Store with each record: prompt version, model, and for each cited chunk the **source, page and a text snippet**, not just the chunk ID, because Phase 15 may re-chunk and change IDs.
- **Persistence:** the app container has no volume today (F-02). Store feedback in SQLite or JSONL on a **named volume** created for this purpose, so it survives deploys and rollbacks. This is a small compose change and does not touch the index. If Phase 15.0 selects Postgres, the feedback table migrates there; keep the schema simple so that migration is trivial.
- Retention period defined (Phase 13.5 logging policy).
- Feedback becomes candidate eval questions only through the existing `generate_candidates` / `review_candidates` flow with manual review. It is never auto-added to the golden dataset.
- Tests: validation, auth, persistence across container recreation, rate limit.

### Phase 14.1 — React frontend

Scope: query box, answer with citations, abstention display, and thumbs up/down plus comment calling `/feedback`. **No upload or delete UI** (*Interim rules*).

**Status: CLOSED 2026-10-30.** Two PRs: (1) the UI on the existing `/query` (#97), (2) a streaming SSE route (#98, merge `857f9a9`, deployed by run `41042230125`; build and deploy green). CI on #98: `pytest` 288 passed / 6 strict xfail, coverage 76.89%; `lint-security`, `build`, `eval`, `Frontend` and CodeQL green; `/query` contract unchanged (no version bump), stream contract `query_stream_final.json` v1. Prod evidence (2026-10-30, through Caddy): UI usable on desktop and phone; feedback row `6558d316-…` (`up`, 09:13:42) rated through the UI on PR 1 and unchanged after the PR 2 deploy (image `857f9a9`); `POST /query/stream` delivers `token` events word by word before `final`. No evaluation numbers are quoted for this sub-phase.

PR 1: #97 (merge `d1821b0`), deployed by run `41027257170` (build, deploy and the new smoke check that `/` serves the UI all green). CI on #97: `pytest`, `lint-security`, `build`, `Frontend` (lint, type check, 11 Vitest tests, build, Playwright e2e at desktop and mobile viewports) and CodeQL green; `/query` contract unchanged. Live 2026-10-30: `/` 200 with `Cache-Control: no-cache` and the CSP meta, hashed bundle 200, `/metrics` still 404. `HEAD /` returns 405 (the route is GET only). Browser round-trip on prod (2026-10-30): query answered in the UI, thumbs up sent ("Feedback recorded"), row `6558d316-…` stored (`up`, outcome `answer`, no comment, 09:13:42 UTC). Survival across a deploy is checked on the PR 2 deploy. Mobile check by Yash on a phone (2026-10-30): fine.

PR 2 (streaming), as built: `POST /query/stream` (same body and key) answers with server-sent events: `token` {text} while generating, then one `final` = `QueryStreamFinal` (every `QueryResponse` field plus `caveat` and `chunks` [{n, source, page, snippet, cited}]), or one `error` {status, error}. Cache hit, abstain and empty send only `final`; `final.answer` is authoritative. Providers retry and fall back only until the first token; after it, a failure ends the stream with `error`. `call_llm(..., on_token=)` streams OpenAI-compatible replies (Ollama arrives in one piece); the pipeline passes `on_token` to generation only, so retrieval and gates are unchanged (the eval fingerprint changes, as code hashes do). `/query`'s cache, logging, tracing and grounding steps moved into helpers both routes share; `/query`'s response is unchanged. Contract: `tests/contracts/query_stream_final.json` v1 and event-sequence tests in `tests/api/test_stream_contract.py`. The UI streams the text, then swaps in `final` and lists each `[SOURCE N]` with file, page, snippet and a cited mark. Local measurement (Windows CPU, one question, corpus c1): first token about 1.2 s before `final`; gpt-oss reasons before it writes, so the gain is mostly the verifier's ~1 s. Groq reports token usage on the stream, so cost accounting stays "reported".

Known limits of the stream route (accepted for one user; revisit in 15.4): the SLO rules and alerts cover `path="/query"` only; the access log and `http_request_duration_seconds` time the stream to its headers, not its end; a provider failure is HTTP 200 with an `error` event, not a 5xx; a client that disconnects mid-answer leaves the pipeline to finish in the background.

Decided 2026-10-30:

- **Stack:** Vite + React + TypeScript in `rag-project/frontend/`, plain CSS; runtime dependencies are only `react` and `react-dom`. Vitest + Testing Library for components, one Playwright e2e test against the production build with the API mocked (desktop and mobile viewports).
- **Hosting:** the build ships in the app image (Dockerfile `web` stage, so Node runs only in CI) and FastAPI serves `/` and `/assets` (`api/main.py` `mount_web`); every other path behaves as before. Chosen over a Caddy-served folder synced by `deploy.sh` because it needs no change to `deploy.sh`, compose or the Caddyfile, and a rollback rolls the UI back with the image. Caddy still fronts it on the same origin, so no CORS.
- **API key:** typed into the UI, kept in `sessionStorage` only. A 401 clears it.
- **Rendering:** plain text only (React escapes it; no markdown library). The production build adds a `<meta>` Content-Security-Policy allowing only same-origin scripts, styles and requests, so injected markup could neither run nor send the key elsewhere.
- **Citations:** `/query` returns `sources` as unique filenames only; the chunk behind each `[SOURCE N]` marker is not in the response. PR 1 shows the markers as text plus the filename list, leaving `/query` unchanged; the streaming route's final event carries the per-chunk `source`, `page`, snippet and `cited` flag so PR 2 maps markers to them.

Decisions to record before building (original brief):

- **API key handling.** The API uses one shared Bearer key; a static single-page app cannot hold a secret. For a single-user system the default is that the user enters the key in the UI and it is kept in memory or `sessionStorage` only; never bake it into the build. Revisit only if the authorization model changes.
- **Hosting.** Preferred: build static files and serve them from the existing Caddy on the same origin (no CORS, no new service, negligible memory). Free static hosting is the alternative and requires CORS to be configured deliberately.
- **Rendering.** Treat answers, citations and source text as untrusted: render as text or sanitised markdown only (document content can contain markup).
- **Streaming (time-to-first-token).** `/query` returns only when the whole pipeline finishes, so the time to first token is the full latency. Add a streaming variant, for example SSE on a new route so the current `/query` contract stays unchanged. It streams generated tokens as they arrive, then sends citation verification, confidence, the caveat and the outcome as a final event. Cache hits are returned as a single event. Add contract tests for the stream format. The UI must handle an answer whose caveat or low-confidence flag arrives after the text.

Quality bar: ESLint and type-check clean, component tests (Vitest or equivalent), and a minimal end-to-end test against a mocked API; a CI job that lints, tests and builds; no new paid service. Keep the UI small: its value is a usable demo of the pipeline and the feedback loop.

Exit: usable on desktop and mobile widths, feedback round-trips and survives a deploy, CI green, `/query` contract tests still pass.

### Post-14 additions (after the close, 2026-10-30)

Not part of the 14.x exit; recorded so Phase 15 starts from what is actually deployed. Both deployed with `7889f26` (Build and Push Image run `41095455566`, build and deploy green). Tests on `main` at `7889f26`: 301 passed / 6 strict xfail, coverage 77.32%.

- **PR #100 — chat UI and 5-turn chat memory** (merge `d779bab`). `QueryRequest` gains an optional `history` (at most `config.HISTORY_TURNS` = 5 turns of `query`, `rewritten_query`, `answer` ≤ `HISTORY_ANSWER_CHARS` = 500; extra fields rejected). It is additive: requests without it behave as before, and the `/query` response contract is unchanged (no version bump). With history, `condense_query` (`CONDENSE_SYSTEM`, LLM stage `rewrite`) turns the follow-up into a standalone question before the cache lookup and retrieval; its LLM call is added to the request's usage. If it fails, the raw follow-up is answered without a cache lookup or store, so it cannot match another chat's cached answer. History is untrusted and used only in the rewrite prompt; Langfuse retention for it is in `Data_Privacy.md`.
- **PR #107 — "Field notes" UI redesign** (merge `7889f26`): serif answers, footnote-style sources, thumbs feedback, system light/dark. Frontend only.

Decisions and limits:
- This bends the 13/14 interim rule against changing retrieval behaviour: for follow-ups, retrieval now sees a condensed question. Accepted because single-turn queries (and so every eval run) take the unchanged path.
- `CONDENSE_SYSTEM` is not part of `PROMPT_VERSION`: the cache and eval key on the standalone question, not on how it was derived.
- Follow-up quality is **not evaluated**: the golden dataset has no multi-turn questions. A follow-up costs one extra LLM call before the first token. Revisit both in 15.2 (stage ablations) if chat use is material.

## Current phase

## Phase 15 — RAG pipeline hardening and scale

Starts after Phase 14 closes. This is where the deferred defects are fixed and the pipeline is measured on the real corpus. Production readiness is not claimed before this phase closes.

**Scope trim (decided 2026-10-31).** One user, $0, a 2 GiB host: Phase 15 keeps what fixes real defects or what the real corpus needs, and drops research-style work whose differences this dataset and free-tier budget cannot resolve.
- **Dropped:** the storage migration (deferred to the 15.1 measurements), multi-format ingestion (the corpus is 100–150 PDFs), reranker alternatives, the no-retrieval / long-context baseline, agentic vs deterministic, the embedding-model experiment, L1 exact-match and L3 retrieval caches, speculative generation.
- **Shrunk:** 15.1 to indexing and measuring the PDF corpus plus dataset v2 (about 20–30 new questions); 15.2 ablations; 15.4 load test and SLO finalisation.
- Revisit a dropped item only with evidence that it fixes a measured problem. The full original plan is in this file's git history before 2026-10-31.

Guard rails: keep the `/query` response schema compatible with the frontend (contract tests from 13.1) or bump the version deliberately; the feedback store is independent of the index, so re-indexing does not touch it.

### Phase 15.0 — Ingestion correctness and PDF upload

Fixes F-01, F-02, F-03, F-27 and removes the matching `xfail` markers, then adds PDF upload and delete from the UI. Two PRs, in this order.

Decided 2026-10-31: the corpus (`c1` now, the 100–150 PDFs in 15.1) is public test data from another GitHub repository, not personal documents, so it may live in git and in the image (check that repository's license before committing the 15.1 set). `IngestRequest.force_reingest` is removed. The BM25 tokenizer is measured only in 15.2.

**Design.** F-01 exists because two copies are kept in step by hand: Chroma (on disk, in-process) and a BM25 index built in memory from `chunks.json`. Make Chroma the single source of truth: build BM25 from the chunks Chroma stores (text and metadata), and drop it after every ingest or delete so the next query rebuilds it. `chunks.json` stops being a serving input. This removes the failure class without a new store. The rebuild swaps a reference, so a query already in flight keeps the old index.

Note on terms: Chroma is not "in-memory"; it persists to disk (SQLite and index files) but runs embedded in the app process, and its HNSW graph is loaded into RAM. What *is* purely in-memory is the BM25 index. The semantic cache in Redis is ephemeral by design.

#### PR 1 — Ingestion correctness

- Check first: Chroma returns every chunk with the text and metadata that BM25 results need. Measure the BM25 rebuild time on `c1` and project it for the 15.1 corpus.
- One ingest function, mostly moved rather than written. Today the API path (`api/routers/ingest.py` `_run_ingest`) scans, deletes before adding, adds to Chroma and clears the cache, but never updates BM25; `scripts/ingest.py` adds to Chroma and rewrites `chunks.json`, but skips the scan, delete-before-add and cache clear. Move the API's sequence into one function in `src/` (for example `ingest_file(path)`), call it from the API and from the script's loop over files, and end it and `_run_delete` with the BM25 reset. The API keeps its path validation and HTTP error mapping; the script stops writing `chunks.json`.
- Remove `force_reingest` from `IngestRequest` (every ingest already re-ingests).
- The Dockerfile keeps building the `c1` index at build time, now through the shared function.
- Check whether the stored `source` string differs between the API and script paths (F-03).
- Retrieval on `c1` must be unchanged (same tokenizer, same chunks): compare against `eval/runs/retrieval_baseline.json`.

Exit PR 1: the five F-01/F-03 strict xfails in `tests/integration/test_ingest_query_delete.py` removed and passing (the injection-scanner xfail is not 15.0's); retrieval on `c1` identical (`corpus c1`, dataset `v1`); `/query` and stream contracts unchanged; deployed.

**PR 1 done 2026-11-02** (#115, merge `ed0e421`, deployed; prod log shows `BM25 index built over 40 chunks`). CI: 309 passed / 1 xfail (injection scanner, not 15.0), coverage 77.69%; eval gate, build and lint green.
- **Evidence ($0, no LLM calls):** on corpus `c1` (`9fc4650202`), dataset `v1` (`51bcd1e330`), prompt `938331ced9a6`, after re-ingesting with the new script, `retrieval_eval` output is identical to `eval/runs/retrieval_baseline.json`, and every stage's chunks and scores (dense/bm25/fused/reranked) are identical for all 46 queries. `chunks.json` byte-identical. `/query` and stream contract snapshots unchanged.
- **Rebuild cost:** about 10 ms warm on `c1` (Chroma read 6 ms). BM25 build alone, measured on replicated `c1` text: 57 ms at 1,200 chunks, 310 ms at 6,000. The Chroma read at those sizes is measured in 15.1.
- **As built:** `store.all_chunks()` (ordered by source, chunk_index, so tie-breaking matches the old order); `BM25Retriever` builds from it (an empty index returns `[]`); `advanced_rag.reset_bm25()` behind a lock (a build that read Chroma before a write cannot be stored after that write's reset); `src/ingestion/ingest.py` `ingest_file(path, notify=True)` and `index_changed()` (cache clear + BM25 reset), called by `POST /ingest`, `DELETE /ingest` and `scripts/ingest.py`. The script processes PDFs sorted by path string, clears the cache once per run (an unreachable Redis costs about 49 s per call on Windows) and exits 1 on any rejected file, so a bad PDF fails the image build. `force_reingest` removed (old clients that send it are ignored).
- **Deviation from the plan above:** the script still writes `chunks.json`, as an eval-only export. The corpus ID, `validate_dataset`, `retrieval_eval`, the candidate tools and the CI "Build chunks" step read it; nothing that serves queries does. Decided 2026-11-01.
- **F-03 `source` check:** both paths already stored the same string for `c1`; `ingest_file` now resolves the path once, so they cannot drift.
- **Limits carried into PR 2:** the BM25 reset is per process (one uvicorn worker today). Running the ingest script inside a live container does not reach the app's BM25, so the re-seed procedure must restart the app.

#### PR 2 — Persistent index and PDF upload from the UI

- **Volumes:** named volumes for Chroma (`/app/storage/chroma`) and the documents folder (`/app/data/documents`) in `docker-compose.prod.yml`. Docker fills an empty named volume from the image on first mount, so the image's index seeds production with no extra code. After that the volume wins: a PDF added to git later reaches prod only by uploading it or by a documented re-seed (remove the volumes, or re-run the ingest script in the container). A rollback to a pre-PR 2 image ignores the volumes and serves its own built-in index; uploads reappear on the next forward deploy.
- **Upload:** a multipart endpoint (for example `POST /documents`, needs `python-multipart`), keyed and rate limited. Accept `.pdf` only, check the `%PDF` header, cap the size, keep only the base name of the filename, save into the documents folder, then call the shared ingest function. A rejected file (injection scan, no text) is removed again. Same name replaces the existing document. One lock around ingest and delete so two writes never interleave.
- **List and delete:** `GET /documents` (name, chunk count) and `DELETE /documents/{name}`, reusing the delete path. The old path-based `/ingest` and `DELETE /ingest` stay blocked at Caddy (local development only); open only the new `/documents` routes.
- **UI:** an upload button (PDF only), the document list, and delete with a confirmation. Names render as plain text; the CSP is unchanged.
- Embedding an uploaded PDF runs on the EC2 instance. That is accepted for one file at a time; bulk loads (15.1) are still built offline.
- Revise the rebuild procedure in `Backup_Recovery.md` (volumes, re-seed, backup of the two volumes).
- The feedback store (`rag_feedback_data`) stays independent of the index; re-indexing never touches it.

Exit PR 2: on prod, a PDF uploaded through the UI is answerable, survives a deploy and a rollback-then-forward, and a deleted one is no longer retrieved by either dense or keyword search; tests for size, type, name handling and the injection rejection; `/query` and stream contracts unchanged; the *Interim rules* about `/ingest` and upload lifted, and the checklist rows for storage, ingestion and backup/restore updated.

**PR 2 done 2026-11-03.** PR #123 (merge `276a5cb`), deployed by run `41461100222`: volumes `rag_chroma_data` and `rag_documents_data` created and seeded from the image (5 PDFs, 40 chunks), Caddyfile synced. CI green (pytest, lint-security, build, frontend, eval, pip-audit, CodeQL); locally 336 passed / 16 skipped / 1 xfail, Vitest 26/26, Playwright 4/4. The pip-audit fix bumped pypdf 6.21.2 → 6.21.4 and pyasn1 0.6.4 → 0.6.5; extracted text and chunks are identical under both pypdf versions.
- **Prod check:** run by the user on the instance (`prodcheck.sh`: upload → cited answer, rollback to `84a7aff` → forward, delete → abstain with BM25 and Chroma back to 40, feedback rows unchanged, Caddy 413 on a 12 MB body, `/ingest` 404) and marked done by the user on 2026-11-03. Its output was not shared, so the individual results (A–I) are not recorded here; the user's direct report is two `/query` calls answered normally after the deploy. A full local rehearsal of the same steps on the release image with a 1 GiB limit passed on 2026-11-02.
- **As built:** one PR. Caps: 10 MiB per file and 1,000,000 extracted characters (`ingest_file(max_chars=)`, checked before the old chunks are deleted). Caddy `request_body /documents max_size 11MiB`, because FastAPI spools a multipart body to disk before the key check runs. One non-blocking lock around upload and delete (busy → 409). Unsafe names are rejected with 400, not stripped. Same name replaces the file, and a failed replace restores the previous one. `GET /documents` lists the PDFs on disk with their Chroma chunk counts. UI: a collapsible Documents panel whose list loads on first open; names render as plain text; CSP unchanged.
- **Measured (local, 1 GiB limit):** a file at the character cap gives 2,107 chunks; anonymous memory 496 → 547 MiB, no OOM, about 90 s.
- **Carry to 15.1:** Chroma refuses a single add of more than 5,461 chunks, and `add_chunks` sends one batch after `delete_by_source` has run. Upload cannot reach it (the character cap), but `scripts/ingest.py` has no cap, so one very large PDF (roughly 800 dense pages) would fail the build. Batch `add_chunks` if the full corpus has such a file.

**Storage decision deferred** to the 15.1 measurements, on real-size data: on `c1` (40 chunks) every candidate fits in memory and answers in milliseconds, so a bake-off now cannot separate them. Triggers for revisiting: BM25 is too big or too slow to rebuild on the full PDF corpus, or ingest has to be transactional. The next step then is SQLite FTS5 + `sqlite-vec` (real BM25, transactional, no extra container), before PostgreSQL + pgvector. Not candidates: Pinecone, managed free-tier Postgres (Supabase, Neon) and Qdrant Cloud (documents leave the host, and free tiers pause or delete idle projects); Elasticsearch/OpenSearch, Milvus and Weaviate (too heavy for a 2 GiB host).

### Phase 15.1 — Full PDF corpus

**Status: DONE 2026-11-04.** PR 1 #125 (merge `81b7855`) and PR 2 #126 (merge `5fd003c`); CI green on both (pytest, lint-security, build, eval gate, CodeQL). `c2` stays offline; prod serves `c1`. Next: 15.2 on `c2` / `v2`.

Addresses F-07, F-08, F-14, F-16, F-17, F-21.

**Decided 2026-10-31: the corpus is PDF only** (sized at 100–150 files then; settled 2026-11-04 as every PDF in the source repository, 236 files). Including every file type would take it past 500 files in eight formats for little gain. The loader already handles PDF (and DOCX, MD and TXT), so no new loaders or format-specific chunking are needed, and the ingest API stays PDF only. Multi-format support (F-15) is closed by this decision; revisit only if the corpus changes.

#### Index and measure

- Index the full PDF set offline through the 15.0 ingest path. One pass: at this size no staged subset is needed.
- Record file count, chunk count, app RSS, startup time, BM25 rebuild time, and query p50/p95. Budget: app steady RSS about 1.0 GiB or less, startup within the compose `start_period`.
- Make the deferred storage decision (15.0) from these numbers. At this size it is expected to confirm Chroma.

#### Decisions (record in `Memory.md`)

1. **Privacy** (F-21): the corpus is public test data (decided 2026-10-31), so it may be committed and shown in the demo. Confirm the source repository's license allows redistribution before committing it.
2. **Cache entity guard:** replace or confine the hard-coded `sedan/suv/hatchback` heuristic (F-14), which breaks once the corpus is not only car manuals.
3. **PDF extraction quality:** spot-check a few PDFs for broken text (the failure analysis found `A<U+202F>ventro`, a brand name split by narrow no-break spaces). Normalise whitespace at load time only if the check shows it matters.

**PR 1 done 2026-11-04** (#125, merge `81b7855`). Two PRs; c2 stays offline, prod serves `c1`.
- **Corpus `c2`:** every `.pdf` under `datasets/` of `github.com/udayallu/RAG-Multi-Corpus` at `39071af3f4dd25e59f5c59a6f9b6e8e99cd643b3` (MIT): 236 files, 6,582,761 bytes, 5 companies (Aventro Motors 50, Cendara University 40, CloudWay-24 37, Velvera Technologies 38, ZX Bank 71). Committed to `rag-project/data/corpus_c2/<Company>/` with `LICENSE`, `SOURCE.md` and `SHA256SUMS`; each file's git blob hash equals the upstream tree entry. Four renames (one `:` Windows cannot store, three leading spaces → `_` as in `c1`), listed in `SOURCE.md`. Excluded from the image by `.dockerignore`. The five `c1` PDFs are byte-identical members of `c2`.
- **Selection:** `RAG_CORPUS=c2` points `config.DATA_DIR`, `STORAGE_DIR` and `CHUNKS_PATH` at `data/corpus_c2`, `storage/chroma_c2` (gitignored) and `storage/chunks_c2.json`; unset is `c1` (CI, image, prod); any other value fails at import. Retrieval eval writes `eval/runs/retrieval_baseline_<corpus>.json`; `retrieval_baseline.json` is the frozen pre-15.1 `c1` record.
- **Index (one pass, `RAG_CORPUS=c2 python scripts/ingest.py`):** 236/236 files, 2,221 chunks, about 4–8 min on the dev laptop (CPU embedding). Largest file 44 chunks, so the 5,461-chunk Chroma limit (line 471 carry) is not reached and `add_chunks` is **not** batched. Corpus id `c2` = `80f20e0aa4` (final, after `clean_text`).
- **First pass rejected 13 files:** the injection scanner's `fake_role_label` matched spec labels (`Operating System:`, `Infotainment System:`, `Banking Assistant:`, `Voice/Assistant:`). The pattern now skips `system:`/`assistant:` directly after `<word> ` or `<word>/`; a role label on its own (line start, after punctuation, `[SYSTEM]:`) is still flagged, and `scanner_eval` is unchanged (INJ01–03 caught, INJ04 missed as before). Accepted gap: `the system: …` is no longer flagged; the prompt boundary remains the main defence.
- **Measured** (local Docker, release image `rag:pr2`, `--memory 1g`, no Redis, no LLM calls; latency over 162 retrievals = 54 cached rewrites × 3):

  | | `c1` (40 chunks) | `c2` (2,221 chunks) | Budget |
  |---|---|---|---|
  | Startup to `pipeline_ready` | 120 s (cold layers, ran first) | 65 s | compose `start_period` 300 s |
  | App idle, cgroup anon | 373 MiB | 430 MiB | |
  | After 162 retrievals, anon / process RSS | 414 / 720 MiB | 506 / 828 MiB | ~1.0 GiB |
  | Chroma read (`all_chunks`) | 18 ms | 310 ms | |
  | BM25 rebuild incl. Chroma read | 20 ms | 377 ms | |
  | Retrieval p50 / p95 (dense + BM25 + RRF + rerank) | 280 / 373 ms | 288 / 401 ms | |

  End-to-end `/query` adds the LLM stages (about 3–4 s, 13.5), which do not depend on corpus size; not re-measured, to save free-tier calls.
- **Storage decision: keep Chroma.** At 55× the chunks, the BM25 rebuild after a write is under 0.4 s, memory is about half the limit and retrieval latency moved by under 30 ms at p95. None of the triggers (BM25 too big or slow, transactional ingest) fired; SQLite FTS5 + `sqlite-vec` stays the next step if one does.
- **F-14 fixed:** the cache entity guard is no longer a word list. A cached answer is served only when both queries have the same content words in the same order (case, punctuation and a tiny filler list ignored; `to`/`from`/`not` kept). Covers every domain (`car loan` vs `bike loan`, `A350` vs `A380`, `One Pro` vs `One Ultra`); the cost is that paraphrases miss. `ENTITY_GROUPS` removed.
- **Extraction:** no U+202F, U+00A0 or zero-width characters in `c2`; the `A<U+202F>ventro` of the failure analysis is a plain space in the extracted text (`A ventro`). The cause is font kerning: a capital is split from its word at kerning pairs (`A ventro`, `V elvera`, `F eatures`, `Y our`), in about a third of `c2` chunks; the brand appeared whole in only 20 chunks against `A ventro` in 135. Also ligatures (`oﬃce`, 9% of chunks) and bullets extracted as U+FFFF (562). The keyword index splits on whitespace, so this matters: `loader.clean_text()` repairs all three at load time (tested; `A` is joined only before v/w/y, so "A car" stays; about 7 known misjoins such as "R and"). On `c1` it changes the text of 15+ of 40 chunks (same boundaries); retrieval on `c1` / `v1` shows no measurable difference (paired, all CIs include 0). New `c1` corpus id `2ef6192555` (was `9fc4650202`). The measurements above were taken before the last `clean_text` rule (same 2,221 chunks).

#### Evaluation after scaling (F-17)

- Keep the 5-PDF corpus `c1` as the CI corpus; CI never ingests the full set.
- Re-run retrieval-only baselines on the full corpus `c2` (no LLM calls needed).
- Spot-check the 27 synthetic questions that have no review record (13.0 item 1, Q17 first) and fix or drop bad labels before dataset v2 is recorded.
- Re-audit every `unanswerable`, `adversarial` and `ambiguous` question against `c2`; new documents can make them answerable.
- Add about 20–30 questions for the new documents, within the free-tier judge budget. The 12-question test split stays frozen. Record `dataset v2 / corpus c2`.
- Report `c1` and `c2` results side by side; do not overwrite `c1` history.

Exit: `c2` ingested through the production path, measurements and the storage decision recorded, dataset v2 validated, baselines filed.

**PR 2 done 2026-11-04** (#126, merge `5fd003c`). CI stays on `c1` / `v1` (unchanged `golden_dataset.json`; `tests.yml` validates it against `c1`).
- **Dataset v2** = `eval/data/golden_dataset_c2.json`, id `a831d87d09` on corpus `c2` `80f20e0aa4`; selected by `RAG_CORPUS=c2` (`eval.paths.GOLDEN_PATH`). 79 questions: the 57 of v1 plus 22 new; 71 answerable; test split the same 12 ids. Validates against `c2` with no errors.
- **Spot-check (13.0 item 1):** the unreviewed synthetic questions are Q31–Q57 (Q16–Q30 have accepted review records). Q17 and all 27 checked against the `c1` text: labels, ground truths and spans correct; no fixes. Q17's failure was the answer, not the label (step 1 of the seat guide is the distance from the pedals).
- **Re-audit against `c2`** (every unanswerable, adversarial and ambiguous question, plus Q57): Q48 (battery capacity) and Q49 (airbags in a Sedan, test split) become `ambiguous`/answer with per-model spans; Q50 (is Roadside Assistance free) becomes answerable (priced per call or per year, `Parts-6.pdf`); Q13 and Q54 stay abstain with reworded ground truths; Q43 gains the service-center list; Q57's support number is in 30 Aventro files, all now `any_of` sources. The others are unchanged. Q49's label was changed although it is in the frozen test split: its v1 label is wrong on `c2`; split membership is unchanged.
- **22 new questions** (Q58–Q79) from upstream `datasets/Dataset categories - queries_01122025.csv` (1,252 queries): seeded sample, 5 per company with query types rotated (all 7 types; Velvera had no usable Temporal question, so Aventro and Velvera have 4). Each `.md` fact mapped to the same-named PDF (with the `SOURCE.md` renames); 48 of 72 tried failed the mapping or span check and were skipped; 8 more were dropped at hand-check (evidence does not answer the question). Ground truth = the upstream fact text (no LLM generation). Origin `upstream`, split `dev`, `ci` false; `company` and `query_type` recorded per item.
- **Baselines** (retrieval-only; 23 new query rewrites on Groq, no judge calls), files in `eval/runs/`: `retrieval_baseline.json` (frozen pre-15.1 `c1`), `retrieval_baseline_c1.json` (`c1` / `v1`), `retrieval_baseline_c2.json` (`c2` / `v2`).

  | Run | n | dense R@5 | BM25 R@5 | fused R@10 | reranked R@5 | reranked MRR |
  |---|---|---|---|---|---|---|
  | `c1` pre-15.1 (`9fc4650202`) | 46 | 0.94 | 0.78 | 0.95 | 0.90 | 0.81 |
  | `c1` / `v1` (`2ef6192555`) | 46 | 0.91 | 0.81 | 0.97 | 0.90 | 0.82 |
  | `c2` / `v2` (`80f20e0aa4`), all | 71 | 0.77 | 0.66 | 0.85 | 0.81 | 0.72 |
  | `c2` / `v2`, the 22 upstream questions | 22 | 0.73 | 0.59 | 0.75 | 0.75 | 0.65 |
  | 44 unchanged v1 labels, `c1` → `c2` | 44 | 0.90 → 0.81 | 0.80 → 0.72 | 0.97 → 0.92 | 0.90 → 0.86 | 0.81 → 0.78 |

  Paired on the 46 shared ids (`c2` − `c1`): dense recall@5 −0.087 (95% CI −0.174 to −0.022), BM25 −0.098 (−0.185 to −0.022), reranked recall@5 −0.033 (−0.109 to +0.022), MRR −0.033 (−0.084 to −0.003); no sign test significant at n = 46. Scaling the corpus 55× costs the first-stage retrievers about 0.09 recall@5, and the reranker absorbs most of it. Weakest: CloudWay-24 (reranked R@5 0.40, n = 5) and questions naming the brand (0.61, n = 14). These are inputs for 15.2.
- Not done here: LLM-judged generation on `c2` (needs the owner's OK and a call count first).

### Phase 15.2 — Retrieval tuning and stage ablations

Use the harness on corpus `c2`. Each experiment is a paired comparison with confidence intervals:

1. **Chunking:** size, overlap, page-boundary merging (F-10). Retrieval-only, $0.
2. **Retrieval:** `TOP_K`, candidate-pool size, and the keyword tokenizer (old vs new). Retrieval-only, $0.
3. **ANN check:** dense retrieval uses Chroma's HNSW with default parameters, never tuned. On the `v2` questions, compare its top-k with an exact brute-force top-k over the same embeddings, at both `TOP_K` and the dense candidate pool (`TOP_K * 4`); report the overlap and any recall difference. If they match, record the default as confirmed; tune HNSW only if they differ. Retrieval-only, $0.
4. **Stage ablations (F-11):** remove query rewriting, the sufficiency judge and citation verification one at a time; keep a stage only if it earns its latency, quota and quality. Also test skipping the rewrite only for short, unambiguous queries, and the follow-up condense step (post-14) if chat use is material.

Dropped 2026-10-31: reranker alternatives, the no-retrieval / long-context baseline, agentic vs deterministic, and the embedding-model experiment.

Use the test split once, at the end. Exit: a written report stating which variants are distinguishable and which are not, with the chosen configuration and rationale.

#### Plan (written 2026-11-05, before any run)

Baseline reproduced first: `RAG_CORPUS=c2 python -m eval.harness.retrieval_eval` rewrote `retrieval_baseline_c2.json` byte-identically (dataset `a831d87d09`, corpus `80f20e0aa4`, prompt version `938331ced9a6`, cached rewrites).

- **Tuning set:** the 61 answerable dev items of `v2` (the 10 answerable test items are not looked at until step 6). Slices, pointers only: company (Aventro 43, Cendara 5, CloudWay-24 5, Velvera 4, ZX Bank 4; company from the item, else from its sources' folder) and brand in query (12).
- **Primary metric:** reranked recall@k and MRR (what generation receives). Also dense R@5, BM25 R@5, fused R@10, mean context characters handed to generation, rerank latency.
- **Statistics:** paired on question id against the base run, `compare.py` (bootstrap 95% CI, sign test). A CI that includes 0 = not distinguishable.
- **Decision rule:** change a setting only on a distinguishable dev improvement with no distinguishable loss on the other primary metric. Ties keep the current code.

| # | Variant | What changes |
|---|---|---|
| 1 | ANN check | Chroma HNSW top-5 / top-20 vs exact cosine over the stored 2,221 vectors: set overlap and paired recall. Tune `ef_search` only if they differ. |
| 2a–e | Chunk size × overlap | 256/64, 256/128, 512/128, 1024/64, 1024/128 (base 512/64). Own index each (`storage/chroma_c2_s<size>o<overlap>`, gitignored). |
| 2f | Page merge | 512/64 with the pages of a file joined before splitting (today a chunk never crosses a page). |
| 2g | Equal context | The 256 variants at `TOP_K` 10, so the context is about the base's 5 × 512 characters. |
| 3a | `TOP_K` | 3, 8 (base 5); pools scale as in the code (first stage ×4, rerank input ×2). |
| 3b | Rerank pool | rerank input 20 and 40 (first-stage depth 20 and 40) at `TOP_K` 5 (base 10 from depth 20). |
| 3c | BM25 tokenizer | `\w+` on lowercased text (punctuation stripped); also that plus a trailing-`s` strip. No stemmer is installed (no NLTK; spaCy has no model), so no real stemming. |
| 4 | Combined | The winners of 1–3, one run. |
| 5 | Ablations (PR 2) | No rewrite (retrieval-only first, $0); then generate/judge for no rewrite, no sufficiency judge, no citation verifier, rewrite only for short queries. Condense step only with evidence of chat use. Call count per provider before each run. |
| 6 | Test split | Chosen configuration vs base, once. |

#### Results

- **1. ANN check (done 2026-11-05):** dataset `a831d87d09`, corpus `80f20e0aa4`, prompt `938331ced9a6`, 61 dev items, `python -m eval.tools.ann_check`. Stored vectors have unit norm (min/max 1.0000). HNSW and exact cosine return identical sets for 61/61 queries at top-5 and top-20 (mean overlap 1.000); dense recall@5 0.779 and recall@20 0.910 for both. Not distinguishable, because they do not differ at all: the default HNSW (`ef_search` 100, `M` 16) is confirmed and not tuned.

All rows below: dataset `a831d87d09`, prompt `938331ced9a6`, 61 answerable dev items, cached rewrites, paired against the base run `r152_base.json` (corpus `80f20e0aa4`, 512/64, `TOP_K` 5: context 2,262 characters, reranked R@5 0.820, MRR 0.721). Δ = variant − base with the bootstrap 95% CI and the sign test (wins/losses, p) from `compare.py`. **Better/worse** = CI excludes 0 and sign test p < 0.05; **n.d.** = not distinguishable. Result files `eval/runs/r152_*.json`. A rerun of the base gave identical metrics.

- **2. Chunking (F-10).** Each variant has its own corpus id. Contains-evidence matching cannot favour small chunks unfairly here: the dev evidence spans are short (median 59, max 184 characters) and fit in some chunk for 112/112 spans at 512 and 1024, 110 at 256/128, 101 at 256/64. Chunk size is bounded by page length (page merge adds 2 chunks), so 1024 chunks average 681 characters, not 1,024.

  | Variant | Corpus id | Chunks | Context chars | Reranked R@k | MRR | Δ R@k (vs base R@5) | Δ MRR | Verdict |
  |---|---|---|---|---|---|---|---|---|
  | 256/64 | `89ac44af60` | 4,573 | 1,116 | 0.563 | 0.507 | −0.257 [−0.369, −0.150] 1/21 | −0.214 [−0.316, −0.115] | worse |
  | 256/128 | `ec41db926c` | 6,387 | 1,116 | 0.661 | 0.571 | −0.158 [−0.254, −0.077] 0/11 | −0.150 [−0.247, −0.056] | worse |
  | 256/64, `TOP_K` 10 | `89ac44af60` | | 2,201 | 0.626 | 0.534 | −0.194 [−0.298, −0.093] 1/16 | −0.187 [−0.288, −0.091] | worse |
  | 256/128, `TOP_K` 10 | `ec41db926c` | | 2,238 | 0.702 | 0.565 | −0.117 [−0.202, −0.049] 0/8 | −0.156 [−0.253, −0.064] | worse |
  | 512/128 | `e3a2b7b41e` | 2,401 | 2,273 | 0.740 | 0.661 | −0.079 [−0.148, −0.022] 0/6 p 0.03 | −0.060 [−0.123, 0.000] p 0.06 | recall worse, MRR n.d. |
  | 512/64, pages merged | `f4b9391056` | 2,223 | 2,255 | 0.803 | 0.705 | −0.016 [−0.049, 0.000] 0/1 | −0.016 | n.d. |
  | 1024/64 | `663f7a683e` | 1,295 | 3,996 | 0.902 | 0.832 | +0.082 [+0.025, +0.156] 6/0 p 0.03 | +0.111 [+0.030, +0.197] 15/5 p 0.04 | better, at 1.77× the context |
  | 1024/128 | `a2e0af635c` | 1,300 | 4,025 | 0.902 | 0.837 | +0.082 [+0.025, +0.156] 6/0 p 0.03 | +0.116 [+0.039, +0.198] 15/4 p 0.02 | better; same as 1024/64 |

  First stage on 1024/64: dense R@5 0.779 → 0.910 (+0.131 [+0.057, +0.213]), BM25 R@5 0.656 → 0.779 (+0.123 [+0.022, +0.230]). Slices, pointers only: CloudWay-24 +0.40 (n = 5, 2/0), brand in query +0.125 (n = 12, 2/0); both CIs include 0. Rerank p50 rises from 30 to 52 ms (longer pairs).
- **3. Retrieval knobs** (base chunking). Rerank latency re-timed on an idle machine: base p50 30 / p95 40 ms.

  | Variant | Context chars | Rerank p50 / p95 ms | Metric | Δ (vs base R@5) | Verdict |
  |---|---|---|---|---|---|
  | `TOP_K` 3 | 1,372 | 22 / 30 | R@3 0.749 | −0.071 [−0.128, −0.025] 0/7 p 0.02; MRR −0.005 | worse |
  | `TOP_K` 8 | 3,614 | 45 / 57 | R@8 0.852 | +0.033 [0.000, +0.074] 3/0 p 0.25; MRR +0.001 | n.d. |
  | rerank input 20 (depth 20) | 2,264 | 56 / 75 | R@5 0.836 | +0.016 [0.000, +0.049] 1/0 | n.d. |
  | rerank input 40 (depth 40) | 2,274 | 109 / 134 | R@5 0.831 | +0.011 [−0.016, +0.049] 1/1 | n.d. |
  | BM25 `\w+` (F-09) | 2,253 | 30 / 45 | BM25 R@5 0.727; reranked R@5 0.820 | BM25 +0.071 [−0.016, +0.164] 9/3 p 0.15; reranked 0.000 | n.d. |
  | BM25 `\w+` + plural strip | 2,258 | 30 / 45 | BM25 R@5 0.735; reranked R@5 0.820 | BM25 +0.079 [−0.011, +0.175] 9/3 p 0.15; reranked 0.000 | n.d. |
  | No rewrite (raw question, 5a) | 2,269 | 31 / 40 | R@5 0.844 | +0.025 [0.000, +0.066] 2/0; MRR +0.011 [−0.036, +0.063] 5/4 | n.d. |

  The tokenizer helps BM25 by itself, but the fused and reranked lists are unchanged, so by the decision rule `lower().split()` stays (F-09). A larger rerank pool costs 2–3.6× the rerank time for nothing measurable. The rewrite earns nothing measurable in retrieval: the raw question is no worse on any stage.
- **4. Combined.** Only chunk size 1024 won, so the combined run is 1024/64 at `TOP_K` 3 (corpus `663f7a683e`), sized to the base's context: 2,380 characters, rerank p50 30 ms. Reranked R@3 0.885 vs base R@5 0.820: +0.066 [+0.016, +0.131], 5/0, sign test p 0.06, so `compare.py` says not distinguishable (the CI excludes 0, the sign test does not reach 0.05); MRR 0.825, +0.104 [+0.024, +0.189] 15/5 p 0.04, better. Dense R@5 +0.131 and BM25 R@5 +0.123, both better. At equal context, the 1024 gain is one distinguishable metric (MRR) plus one borderline (recall).
- **5. Ablations (F-11, done 2026-11-06).** Dataset `a831d87d09`, corpus `663f7a683e`, prompt `938331ced9a6`, chosen configuration (`RAG_CORPUS=c2 RAG_CHUNK_SIZE=1024 RAG_TOP_K=3`, generation fingerprint `77cea887f6`), all 67 dev items (61 answerable, 6 unanswerable). Pipeline Groq `gpt-oss-120b`, verifier Groq `qwen/qwen3.8-27b`, judge Gemini; 0 judge failures. Rewrites are cached in every arm, so the rewrite call's own cost and latency are not in these numbers. Behaviour = correct answer or correct abstention.

  | Ablation | How measured | Behaviour | Correctness | Faithfulness | Relevancy | Cost of the stage | Verdict |
  |---|---|---|---|---|---|---|---|
  | No rewrite | full arm, 67 runs | −0.030 [−0.119, +0.060] 4/6 | +0.008 [−0.032, +0.049] 3/2 | −0.010 [−0.027, 0.000] 0/2 | +0.004 [−0.013, +0.020] 27/18 | 1 `gpt-oss` call per query (not measured: cached) | n.d. |
  | No sufficiency judge | re-run the 16 questions it refused or that should abstain; the other 51 cannot change | +0.060 [+0.015, +0.119] 4/0 p 0.12 | 0 on shared ids; the 4 new answers score 1.0, 1.0, 0.5, 0.5 | 0; new answers 1.0 | 0 | 1 `gpt-oss` call per query, ~900 tokens (≈40% of the pipeline's `gpt-oss` tokens) | n.d. (CI excludes 0, sign test does not) |
  | No citation verifier | derived: it never blocks, and the judge strips its caveat | 0 | 0 | 0 | 0 | 1 `qwen` call per answer, ~960 tokens (separate quota) | n.d.; it flagged 2 answers low-confidence, both weak (correctness 0.5, 0.0 vs 0.86 for the rest) |
  | Rewrite only for ≤ 8-word questions | derived: `no_rewrite` record for the 7 short questions, `baseline` otherwise | 0 | 0 | 0 | −0.001 [−0.004, +0.001] 2/4 | saves 7 of 67 rewrite calls | n.d. |

  Sign = ablation − baseline; wins/losses are for the ablation. Without the sufficiency judge the generator refuses on its own ("don't have enough information") for 6 of the 10 answerable questions the judge blocked and for 5 of the 6 unanswerable ones. The one unanswerable question answered (Q13) is answered with the judge too. So on dev the judge blocked 4 answerable questions and caught no unanswerable one that the generator would have missed. Without the rewrite, the judge refuses 13 answerable questions instead of 10. The condense step is not tested: there is no evidence of chat use (single user, no multi-turn traffic measured).
- **6. Test split (run once, 2026-11-05 retrieval, 2026-11-06 generation).** Dataset `a831d87d09`, prompt `938331ced9a6`, 12 test items (10 answerable). Retrieval: base `r152_final_base.json` (corpus `80f20e0aa4`, 512/64, `TOP_K` 5): reranked R@5 0.750, MRR 0.733, context 2,294 characters. Chosen `r152_final_chosen.json` (corpus `663f7a683e`, 1024/64, `TOP_K` 3): R@3 0.817, MRR 0.850, context 2,475 characters. Paired: recall +0.067 [−0.100, +0.300] 1/1; MRR +0.117 [0.000, +0.317] 2/0 p 0.50. Generation (base fingerprint `4bb5ee4d52`, chosen `77cea887f6`), chosen − base: behaviour +0.083 [0.000, +0.250] 1/0 (0.833 → 0.917; the chosen configuration answers one more answerable question, correctness 0.4); correctness and faithfulness tied on the 8 shared answers; relevancy +0.008 [−0.023, +0.042] 4/4. All n.d., as expected at n = 12. Direction matches dev, with no reversal.

#### Report (retrieval part, experiments 1–4; dataset `a831d87d09`, prompt `938331ced9a6`, dev n = 61)

| Distinguishable | Not distinguishable |
|---|---|
| Chunk size 1024 (better on R@5, MRR, dense and BM25 R@5; overlap 64 vs 128 makes no difference) | HNSW vs exact (identical) |
| Chunk size 256 at either overlap, at `TOP_K` 5 and 10 (worse) | Page merge |
| Overlap 128 at 512 (recall worse) | `TOP_K` 8; rerank input 20 / 40 |
| `TOP_K` 3 on 512 chunks (worse) | BM25 `\w+` and `\w+` + plural strip, for the fused and reranked lists (F-09) |
| 1024/64 at `TOP_K` 3 vs base: MRR better (recall +0.066, CI excludes 0, sign test p 0.06) | No rewrite, retrieval only |

**Chosen configuration (owner delegated the choice, 2026-11-05): chunk size 1024, overlap 64, `TOP_K` 3, everything else unchanged** (pool `TOP_K` × 4, RRF 60, `lower().split()`, default HNSW). Rationale: it is the only change with a distinguishable gain. At `TOP_K` 3 it hands generation about the same context as today (2,380 vs 2,262 characters), so the gain cannot come from extra context or extra prompt tokens. `TOP_K` 5 on 1024 chunks would raise recall a little more (0.902), but it needs 1.77× the context, about +430 prompt tokens per answer on free-tier Groq. Overlap 128 adds nothing. This choice holds for `c2` only. Shipping it to prod/CI (`c1`) needs a `c1` re-index, a new CI gate baseline and a re-seed of B in `Backup_Recovery.md`, and the owner has not decided that. Until then `RAG_CHUNK_SIZE` / `RAG_TOP_K` select it on `c2` and are refused on `c1`.

#### Report (stages, experiments 5–6; dataset `a831d87d09`, corpus `663f7a683e`, prompt `938331ced9a6`, dev n = 67)

No stage ablation is distinguishable on any judged metric. The rule was "keep a stage only if it earns its latency, quota and quality", so each stage is judged on its cost:

| Stage | Earns | Costs | Recommendation (owner decides: removing a stage changes the API response) |
|---|---|---|---|
| Query rewrite (single turn) | nothing measurable: retrieval with the raw question is no worse (5a), generation n.d. | 1 `gpt-oss` call and one round-trip per query | Drop it for single-turn queries. Keep the follow-up condense step, which shares the module and was not tested. `rewritten_query` would then equal the query. |
| Sufficiency judge, LLM tier | nothing measurable: the generator refuses on its own for every unanswerable question the judge caught | ~900 `gpt-oss` tokens per query (≈40% of the pipeline's), and it blocked 4 answerable questions | Drop the LLM tier and keep the $0 cross-encoder floor. `sufficiency.tier` would no longer report `llm_judge`. |
| Citation verifier | a low-confidence flag that marked the 2 weakest answers (n = 2, pointer only) | 1 `qwen` call per answer on a separate quota | Keep. |
| Rewrite only for short questions | nothing (7 short dev questions; no difference) | adds a rule | Do not build. |

With both recommended removals, a query makes 1 `gpt-oss` call instead of 3, plus the verifier. That combination was not run as one arm. Re-run the dev generation once before shipping it.

**Test split (once):** chosen vs base is n.d. on every retrieval and generation metric at n = 12, in the same direction as dev. No result reverses.

**Phase status:** experiments 1–6 done. Three owner decisions are open: (1) ship 1024/64 at `TOP_K` 3 to `c1`/prod (re-index, CI gate, re-seed B); (2) whether prod moves to `c2`; (3) the two stage removals above. **Decided 2026-11-06: (3) no.** The owner keeps all four stages, so the pipeline architecture and API response stay unchanged. The measurements stay on record.

### Phase 15.3 — Token and cache optimization

**Dropped as a build step (2026-10-31).** With one user there are few exact repeats or colliding rewrites, so L1 exact-match and L3 retrieval caches would rarely hit, and speculative generation spends free-tier Groq tokens on abstained queries to save about one round-trip.

- Already done: connection reuse (2026-10-26; one pooled `requests.Session` in `src/llm/client.py`). The L2 semantic cache (Phase 9) stays.
- Revisit only if the 13.4 log fields (`cache_exact_repeat`, `rewritten_query_hash`) or the 15.4 load test show a stage that caching would fix. The original design (keys, TTLs, `clear_cache()` rules, rejected options) is in this file's git history before 2026-10-31.

### Phase 15.4 — Final operational validation

- One short load test (k6) at 5–10 concurrent users on the real instance; record p50/p95 and anything that fails. That is the capacity statement (F-16).
- Keep the provisional SLOs: single-user traffic is too noisy to tune against. Say so in `Observability.md`, and re-check memory limits against `c2`.
- Run `prompts/workflows/production-readiness-review.md` and file the result.
- **Upgrade torch from 2.6.0 and audit it.** Dependabot has 8 open torch advisories (memory corruption or DoS in `torch.jit.script`, `lstm_cell`, `pad_packed_sequence`, `unpack_sequence`, …; left open on purpose 2026-10-29). We call none of those functions directly, so the risk is low. Dependabot only reads `requirements-local.txt`; the prod `Dockerfile` installs `torch==2.6.0` from the CPU index on its own line, which neither Dependabot nor `pip-audit` sees. Upgrade both, and put the prod torch version where `audit.yml` checks it. The upgrade can shift embedding and reranker scores, so re-run the retrieval baseline and the eval gate on `c2` before and after.
- Add a container image scan (F-22), for example a free Trivy step in `build-push.yml`.

Exit: the *Production-readiness checklist* has no open gaps, or each remaining one is accepted and recorded with a reason.

## Production-readiness checklist

Status as of 2026-10-30 (Phase 14 closed). Gap items name the owning phase.

| Area | Status | Owner / evidence |
| --- | --- | --- |
| Hybrid retrieval, reranking, grounded answers with citations, abstention | Done | Phases 2, 8 |
| Prompt-injection defense | Partial — scanner on every ingest path since 15.0 PR 1 (API and script); soft injection (INJ04) still missed | F-03 fixed (#115) |
| Auth (shared key), rate limiting, HTTPS | Done — single-user by decision (one shared key) | Phases 9, 12; decision 13.5 (`Security.md`) |
| Automated deployment, health check, rollback | Done, verified live; rollback drilled again 2026-10-29 | Phase 12, 13.5 |
| Regression evaluation in CI | Partial — LLM-judge gate on 4 items, path-filtered and advisory; `c1` cannot discriminate variants. Offline `c2` evaluation can discriminate retrieval variants (15.2); CI stays on `c1` until prod moves | F-07, F-08 → 15.1, 15.2; CI on `c2` only if prod moves (owner) |
| Unit / API / integration tests in CI | Done — required `pytest` check, 301 passed, coverage 77.32% (`main` at `7889f26`) | 13.1 |
| Reproducible builds (pinned dependencies) | Done — lock files; image built on every pipeline PR | 13.1 |
| Dependency / image vulnerability scanning | Partial — pip-audit, Dependabot and CodeQL done; no container image scan; prod torch 2.6.0 not audited (8 open advisories) | F-22, torch upgrade → 15.4 |
| Prompt / model versioning | Done — `config.PROMPT_VERSION` in responses, logs, metrics, cache namespace and eval records | 13.2, PR #67 |
| Per-stage cost and latency visibility | Done — LLM stages (tokens, latency, reported vs estimated) and retrieval stages | 13.3, 13.4 |
| Request correlation and tracing | Done — one request ID across response, logs and Langfuse trace | 13.4 |
| Alerting and SLOs | Done, provisional — availability and latency SLOs, burn-rate alerts by email, fire-tested on prod | 13.5; final numbers → 15.4 |
| External uptime monitoring | Done — `Uptime` workflow every 10 min, fire-tested | 13.5 |
| Resource limits on containers | Done — `mem_limit` on all services, Redis `maxmemory`, verified live | 13.5; re-check → 15.4 |
| Secrets without long-lived keys | Accepted — OIDC blocked by the AWS-managed SCP; least-privilege deploy key, 90-day rotation (next 2027-01-27) | F-18, 13.5; re-check → 15.4 |
| Logging / retention policy and log rotation | Done — policy in `Data_Privacy.md`, rotation active; feedback text 90 days | 13.5, 14.0 |
| User feedback loop | Done — `POST /feedback` (server-side grounding, SQLite on a named volume) and the UI thumbs + comment; round-trip and deploy survival verified on prod | 14.0, 14.1, PRs #95, #97 |
| Usable front end | Done — React UI on the same origin, streaming answers with mapped citations, abstain/low-confidence display, feedback; verified on desktop and phone | 14.1, PRs #97, #98 |
| Storage architecture fit for production | Partial — Chroma is the single source of truth since 15.0 PR 1 (BM25 rebuilt from it); index and documents persisted in named volumes since PR 2; store choice deferred to the 15.1 measurements | F-27 fixed (#115); 15.1 |
| Ingestion correct and persistent | Done — correct since 15.0 PR 1; persistent on prod in named volumes since PR 2; upload, list and delete from the UI | F-01, F-02, F-03 fixed (#115, #123) |
| Supports the real corpus formats | Done by decision — the corpus is 100–150 PDFs; the loader also reads DOCX, MD and TXT | F-15, decided 2026-10-31 |
| Evaluation that can discriminate variants | **Done for retrieval on `c2`** (15.2, 2026-11-05): paired CI + sign test separate chunking variants on 61 dev items (1024 better, 256 worse). Generation metrics on dev showed no distinguishable stage effect at n ≈ 56; the 10-item test split cannot discriminate (n.d. on both metrics). CI still gates on `c1` | F-07, F-08 → 15.1; 15.2 |
| Corpus versioning and privacy decision | **Gap, deferred** | F-21 → 15.1 |
| Load test and capacity statement | **Gap, deferred** | F-16 → 15.4 |
| Backup / restore procedure | Done — both index volumes backed up and restored by hand, re-seed A/B and the rollback rules in `Backup_Recovery.md`; rehearsed locally 2026-11-02; revisit if storage changes | 15.0 PR 2 |

## Later roadmap — order: 16 → 17, after Phase 15

Confirm scope before starting each phase.

### Phase 16 — RAG portfolio and reusable eval kit

Merged 2026-11-04 from the former Phase 16 (Graph RAG + Multimodal RAG) and Phase 17 (Portfolio extraction). Output: six RAG variants as portfolio projects — Naive, Advanced, Production, Agentic, Graph and Multimodal RAG — measured with one shared eval kit, so they report comparable numbers in one table. Lightweight items for this repository (README accuracy, an architecture diagram, the evaluation write-up) are still produced during Phases 13–15, not deferred here.

**Decisions (2026-11-04, do not re-ask):**

- **Production RAG is this live repository,** not a frozen snapshot. Phase 17 extends it, and its portfolio entry is updated then.
- **Naive, Advanced and Agentic RAG start from the owner's existing project folders** (kept outside this repository; not in its git history). They are updated in place, not rebuilt. Agentic RAG may still need real build work: this repository has only its foundations (`src/agent/`), and agentic vs deterministic was dropped from 15.2.
- **Those folders are never committed here.** Workflow: at the start of the sub-phase, move the folder into this project's root; update it (corpus `c2`, dataset `v2`, the eval kit); move it out again; it is published from its own separate repository. While a folder is in the root:
  - add it to `.git/info/exclude` (local, not committed), so `git add` cannot pick it up;
  - keep it out of the committed knowledge graph: exclude it from graphify, or run `graphify update .` only after it has been moved out;
  - it is outside `rag-project/`, the Docker build context, so the image and CI are unaffected.
- **Graph and Multimodal RAG are showcase builds.** The former evidence entry condition is dropped; each write-up says the project is a showcase, and each gets questions it should win (multi-hop for Graph; image and table questions for Multimodal).
- Technologies (LangChain, LangGraph, LlamaIndex, Langfuse, …) are chosen from each project's requirements, not in advance.
- **Free tier:** retrieval metrics for every variant ($0); LLM-judged runs on a small subset per project, with the call count stated before each run.

#### 16.0 — Eval kit

- Extract `rag-project/eval/` into a standalone package that every project uses. Today it imports this app directly (`retrieve_context`, `src.llm.client`, `config`, `src.vectorstore.store`, the citation pattern); replace those with an adapter interface: `retrieve(query) → ranked chunks with source and page`, `answer(query) → answer and contexts`.
- Keep: dataset schema and validator, retrieval metrics, paired comparison with confidence intervals (`compare.py`), gate, judge (LLM client pluggable), dataset and corpus identifiers on every record. Add question categories (multi-hop, image, table).
- Check first: dataset labels are chunk-independent (source and page, not chunk ID); otherwise variants that chunk differently cannot be compared.
- Exit: Production RAG run through the kit reproduces its `c2` retrieval baseline exactly.

#### 16.1 — Naive and Advanced RAG

- The existing folders, moved in, updated to `c2` and dataset `v2`, measured with the kit, moved out to their own repositories.

#### 16.2 — Agentic RAG

- The existing folder, moved in and updated the same way as 16.1; compared with Production RAG on quality, latency and LLM calls per query.

#### 16.3 — Graph RAG

- Multi-hop questions added to the dataset (hand-checked, as in 15.1).

#### 16.4 — Multimodal RAG

- Needs a corpus with material image or table content; check whether `c2` has it before choosing one.

#### 16.5 — Write-up

- One cross-variant table (same corpus, dataset and metrics), stating which differences are distinguishable and which are not; a README and architecture diagram per project.
- Each finished project is preserved as a standalone artifact; do not casually modify it afterwards. The live Production RAG repository is the exception.

### Phase 17 — Multi-tenancy and RBAC

Added 2026-11-04 (first numbered 18). Starts after Phase 16 and extends the live Production RAG repository; update its portfolio entry when done. It supersedes F-19 (single user, one shared key, every key holder sees the whole corpus): record the new decision in `Security.md` when the phase starts.

**Goal:** a portfolio demo, live on prod, of tenant isolation and role and document permissions enforced at every pipeline stage, not only at authentication. No real outside users; $0 and the single `t3.small` still apply.

**Decisions (2026-11-04, do not re-ask):**

- **Identity:** a server-side map from API key to a principal `{tenant_id, user_id, role}`. `verify_api_key` returns the principal instead of the key hash; an unknown key is a 401. Cognito or other real sign-in is out of scope.
- **Isolation:** one shared Chroma collection. Every chunk carries `tenant_id` and `doc_id`, and every read filters on them.
- **RBAC:** roles `viewer` (query), `editor` (+ upload and delete in its tenant), `admin` (+ manage document access). Per-document access inside a tenant lives in a table, not in chunk metadata, and is resolved per request to a list of allowed doc IDs, so a revocation takes effect on the next query without rewriting chunks.
- **Store:** SQLite on a named volume (the feedback store pattern) for principals and document access. Keys stored hashed; a small admin script manages them.
- **Cache scope:** the semantic cache namespace adds `tenant_id` and an access-scope hash (hash of the sorted allowed doc IDs). Users with the same access share entries; a revocation changes the hash, so a cached answer holding snippets from a lost document is never served. Rejected: `tenant + user` (needs an explicit clear on every access change; a missed clear leaks).
- **Prod:** deployed. `c2` is split by company into 5 tenants (ZX Bank, Aventro, Cendara, Velvera, CloudWay-24) with demo keys per role.
- **Principle:** filter before ranking. Dense and BM25 apply the scope before their `top_k` cut; the reranker is never relied on to drop forbidden chunks.

**Entry checks:**

- The 15.4 memory re-check shows headroom for `c2` on prod (prod serves `c1` today).
- Confirm the AWS plan and credit status (hard constraint above).
- Confirm the installed Chroma version supports the `where` filters needed (`$and`, `$in` on `doc_id` with up to the largest tenant's document count, 71 in `c2`).

#### PR 1 — Tenancy

- Principal, SQLite store and admin script; every route receives the principal.
- Ingest: `tenant_id` and `doc_id` in chunk metadata; `tenant_id` in `_chunk_id` (same path in two tenants must not collide); a documents folder per tenant; `delete_by_source` and `GET`/`DELETE /documents` scoped to `{tenant_id, source}`.
- Retrieval: one `scope_filter(principal)` used by every read path — dense (`similarity_search(filter=…)`), BM25 (one index per tenant, rebuilt from Chroma with the tenant filter; keeps term statistics separate), the agent tool (`src/agent/tools.py`) and `/documents`. The eval harness passes an explicit eval principal; no unscoped call path remains.
- Fail-closed check after fusion, before rerank: drop and log any chunk outside the principal's scope.
- Cache namespace gains `tenant_id`; `index_changed()` clears only that tenant's entries.
- Langfuse traces and feedback rows carry `tenant_id`; feedback reads are tenant-scoped.
- Tests: two tenants with the same filename and different content — no cross-tenant chunk at the dense, BM25, fused or reranked stage; a tenant A cache entry misses for tenant B; a re-upload in A leaves B's chunk count unchanged; an unknown key gets 401.

#### PR 2 — RBAC

- Roles enforced per route (403 on a denied action); the UI shows tenant and role and hides upload and delete for viewers (the server still enforces).
- Document access table; allowed doc IDs resolved per request; dense filters `doc_id $in […]`, BM25 masks scores before the `top_k` cut.
- Access-scope hash in the cache namespace.
- Tests: a viewer gets 403 on upload; a revoked document is not retrieved and the next query misses the cache; two users with the same access share a cache hit.

**Exit:**

- Isolation and RBAC tests green in CI; on prod, a question about another tenant's documents abstains, verified per role.
- Retrieval eval run per tenant on `c2` and recorded as a new baseline; differences from the 15.2 baseline explained (per-tenant BM25 changes term statistics).
- The 15.4 load test re-run on prod with several tenants; memory recorded.
- `Security.md`, `Architecture.md` and `Data_Privacy.md` updated; F-19 marked superseded.

**Out of scope:** real sign-in (Cognito), self-service tenant sign-up, a collection per tenant, an audit-log UI, a database migration.

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
