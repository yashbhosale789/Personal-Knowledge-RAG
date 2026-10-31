# Personal Knowledge OS — Detailed Roadmap (working plan)

Last reconciled: 2026-10-29

Current phase: **Phase 14 — Human feedback and React frontend** (Phase 13 closed 2026-10-29)

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
| F-15 | Loader handles 4 formats and the ingest API only `.pdf` | None: the corpus is PDF only (decided 2026-10-31) | None | Closed by decision |
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

### Phase 15.0 — Ingestion correctness on Chroma

Fixes F-01, F-02, F-03, F-27 (and F-09 if the harness shows it helps) and removes the matching `xfail` markers. One sub-phase, one or two PRs.

**Design.** F-01 exists because two copies are kept in step by hand: Chroma (on disk, in-process) and a BM25 index built in memory from `chunks.json`. Make Chroma the single source of truth: build BM25 from the chunks Chroma stores (text and metadata), and drop it after every ingest or delete so the next query rebuilds it. `chunks.json` stops being a serving input. This removes the failure class without a new store. The rebuild swaps a reference, so a query already in flight keeps the old index.

Note on terms: Chroma is not "in-memory"; it persists to disk (SQLite and index files) but runs embedded in the app process, and its HNSW graph is loaded into RAM. What *is* purely in-memory is the BM25 index. The semantic cache in Redis is ephemeral by design.

- Check first: Chroma returns every chunk with the text and metadata that BM25 results need. Measure the BM25 rebuild time on `c1` and project it for the 15.1 corpus.
- One ingest function, mostly moved rather than written. Today the API path (`api/routers/ingest.py` `_run_ingest`) scans, deletes before adding, adds to Chroma and clears the cache, but never updates BM25; `scripts/ingest.py` adds to Chroma and rewrites `chunks.json`, but skips the scan, delete-before-add and cache clear. Move the API's sequence into one function in `src/` (for example `ingest_file(path)`), call it from the API and from the script's loop over files, and end it and `_run_delete` with the BM25 reset. The API keeps its path validation and HTTP error mapping; the script stops writing `chunks.json`.
- `IngestRequest.force_reingest` is accepted but ignored (every ingest re-ingests): remove it or make it work.
- Index lifecycle: Chroma on a **named volume** and an **offline-built index**, replacing `RUN python scripts/ingest.py` in the Dockerfile. Build on the dev machine, not on the EC2 instance (CPU credits, live-traffic starvation). API ingest and delete then persist across deploys. Revise the rebuild procedure in `Backup_Recovery.md`.
- BM25 tokenizer: regex word tokens instead of `split()`; keep only if the harness shows it helps.
- Check whether the stored `source` string differs between the API and script paths (F-03).
- The feedback store (`rag_feedback_data`) stays independent of the index; re-indexing never touches it.

**Storage decision deferred** to the 15.1 measurements, on real-size data: on `c1` (40 chunks) every candidate fits in memory and answers in milliseconds, so a bake-off now cannot separate them. Triggers for revisiting: BM25 is too big or too slow to rebuild on the full PDF corpus, or ingest has to be transactional. The next step then is SQLite FTS5 + `sqlite-vec` (real BM25, transactional, no extra container), before PostgreSQL + pgvector. Not candidates: Pinecone, managed free-tier Postgres (Supabase, Neon) and Qdrant Cloud (personal documents leave the host, and free tiers pause or delete idle projects); Elasticsearch/OpenSearch, Milvus and Weaviate (too heavy for a 2 GiB host).

Exit: the five F-01/F-03 strict xfails in `tests/integration/test_ingest_query_delete.py` removed and passing (the injection-scanner xfail is not 15.0's); retrieval on `c1` unchanged or the difference reported (paired, `corpus c1`, dataset `v1`); `/query` and stream contracts unchanged; ingest through the API survives a deploy and a rollback; the *Interim rules* about `/ingest` lifted and the checklist rows for storage, ingestion and backup/restore updated.

### Phase 15.1 — Full PDF corpus

Addresses F-07, F-08, F-14, F-16, F-17, F-21.

**Decided 2026-10-31: the corpus is PDF only, 100–150 files.** Including every file type would take it past 500 files in eight formats for little gain. The loader already handles PDF (and DOCX, MD and TXT), so no new loaders or format-specific chunking are needed, and the ingest API stays PDF only. Multi-format support (F-15) is closed by this decision; revisit only if the corpus changes.

#### Index and measure

- Index the full PDF set offline through the 15.0 ingest path. One pass: at this size no staged subset is needed.
- Record file count, chunk count, app RSS, startup time, BM25 rebuild time, and query p50/p95. Budget: app steady RSS about 1.0 GiB or less, startup within the compose `start_period`.
- Make the deferred storage decision (15.0) from these numbers. At this size it is expected to confirm Chroma.

#### Decisions (record in `Memory.md`)

1. **Privacy** (F-21): keep the personal corpus out of git and out of any public repo; decide what the public demo indexes.
2. **Cache entity guard:** replace or confine the hard-coded `sedan/suv/hatchback` heuristic (F-14), which breaks once the corpus is not only car manuals.
3. **PDF extraction quality:** spot-check a few PDFs for broken text (the failure analysis found `A<U+202F>ventro`, a brand name split by narrow no-break spaces). Normalise whitespace at load time only if the check shows it matters.

#### Evaluation after scaling (F-17)

- Keep the 5-PDF corpus `c1` as the CI corpus; CI never ingests the full set.
- Re-run retrieval-only baselines on the full corpus `c2` (no LLM calls needed).
- Spot-check the 27 synthetic questions that have no review record (13.0 item 1, Q17 first) and fix or drop bad labels before dataset v2 is recorded.
- Re-audit every `unanswerable`, `adversarial` and `ambiguous` question against `c2`; new documents can make them answerable.
- Add about 20–30 questions for the new documents, within the free-tier judge budget. The 12-question test split stays frozen. Record `dataset v2 / corpus c2`.
- Report `c1` and `c2` results side by side; do not overwrite `c1` history.

Exit: `c2` ingested through the production path, measurements and the storage decision recorded, dataset v2 validated, baselines filed.

### Phase 15.2 — Retrieval tuning and stage ablations

Use the harness on corpus `c2`. Each experiment is a paired comparison with confidence intervals:

1. **Chunking:** size, overlap, page-boundary merging (F-10). Retrieval-only, $0.
2. **Retrieval:** `TOP_K`, candidate-pool size, and the keyword tokenizer (old vs new). Retrieval-only, $0.
3. **Stage ablations (F-11):** remove query rewriting, the sufficiency judge and citation verification one at a time; keep a stage only if it earns its latency, quota and quality. Also test skipping the rewrite only for short, unambiguous queries, and the follow-up condense step (post-14) if chat use is material.

Dropped 2026-10-31: reranker alternatives, the no-retrieval / long-context baseline, agentic vs deterministic, and the embedding-model experiment.

Use the test split once, at the end. Exit: a written report stating which variants are distinguishable and which are not, with the chosen configuration and rationale.

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
| Prompt-injection defense | Partial — API path only | F-03 → 15.0 |
| Auth (shared key), rate limiting, HTTPS | Done — single-user by decision (one shared key) | Phases 9, 12; decision 13.5 (`Security.md`) |
| Automated deployment, health check, rollback | Done, verified live; rollback drilled again 2026-10-29 | Phase 12, 13.5 |
| Regression evaluation in CI | Partial — LLM-judge gate on 4 items, path-filtered and advisory; `c1` cannot discriminate variants | F-07, F-08 → 15.1, 15.2 |
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
| Storage architecture fit for production | **Gap, deferred** — Chroma becomes the single source of truth; store choice deferred to the 15.1 measurements | F-27 → 15.0, 15.1 |
| Ingestion correct and persistent | **Gap, deferred** | F-01, F-02, F-03 → 15.0 |
| Supports the real corpus formats | Done by decision — the corpus is 100–150 PDFs; the loader also reads DOCX, MD and TXT | F-15, decided 2026-10-31 |
| Evaluation that can discriminate variants | **Gap, deferred** | F-07, F-08 → 15.1 |
| Corpus versioning and privacy decision | **Gap, deferred** | F-21 → 15.1 |
| Load test and capacity statement | **Gap, deferred** | F-16 → 15.4 |
| Backup / restore procedure | Partial — index rebuild documented (`Backup_Recovery.md`); revised when storage changes | 13.5 → 15.0 |

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
