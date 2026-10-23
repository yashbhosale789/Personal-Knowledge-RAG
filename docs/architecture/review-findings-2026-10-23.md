# Production-Readiness Review — Findings (2026-10-23)

Scope: roadmap, `Memory.md`, `Architecture.md`, and the code paths they describe.
Each finding carries a **confidence tag** so nothing here is mistaken for a measured fact:

- **[Verified]** — read directly in the repo at the time of review.
- **[Measured]** — produced by a repo artifact (e.g. `eval/runs/compare_report.txt`).
- **[Estimate]** — my arithmetic from repo numbers; measure before relying on it.
- **[Unverified]** — inferred, or taken from `Memory.md` without re-checking.

Nothing below has been fixed yet. The roadmap (`docs/context/Roadmap.md`) assigns each finding to a phase.

## Corrections to the first review

| First-review claim | Status |
|---|---|
| BM25 index goes stale after `/ingest` | **Confirmed, and worse** — see F-01. |
| Semantic cache has no invalidation on corpus change | **Wrong.** `/ingest` and `DELETE /ingest` both call `clear_cache()`, and `deploy.sh` flushes `cache:*`. What is still true: the cache key is `sha256(query)` with no prompt, model or corpus version (F-14). |
| Unit tests may not run in CI | **Confirmed** — no workflow contains `pytest` (F-04). |

## A. Correctness and production-integrity bugs

**F-01 — BM25 ignores API-ingested documents and keeps serving deleted ones. [Verified by reading; not reproduced]**
`_bm25 = BM25Retriever()` is built once at import (`src/pipeline/advanced_rag.py:21`) from `storage/chunks.json`. Only `scripts/ingest.py` writes that file. `POST /ingest` writes to Chroma only; `DELETE /ingest` removes from Chroma and deletes the PDF, but the chunks stay in `chunks.json` and in the in-memory BM25 index. Consequences: new documents are invisible to keyword search even after a restart; deleted documents' text can still be retrieved and sent to the LLM.

**F-02 — In production the index is baked into the Docker image; `/ingest` and `DELETE` do not persist. [Verified]**
`Dockerfile` runs `python scripts/ingest.py` at build time. `docker-compose.prod.yml` mounts no volume for `app`. A new image recreates the container, so anything ingested or deleted through the API is lost on the next deploy, and a rollback restores the older baked index. The two endpoints are effectively demo-only in production.

**F-03 — Two ingestion paths with different safety properties. [Verified]**
The API path scans for prompt injection, deletes prior chunks for the source, adds chunks, and clears the cache. `scripts/ingest.py` (also used by the Dockerfile and the CI eval gate) does none of these. It calls `add_chunks` directly, so a document that shrinks leaves stale tail chunks, and the injection scanner never sees bulk-ingested files. `Memory.md` places the Phase 11 idempotency fix "in `store.py`"; in the code, the delete-before-add lives in the router, not in `add_chunks`. The same file may also get different `source` strings from the two paths (relative vs resolved absolute), which would duplicate it. [Unverified: check the stored `source` values.]

**F-04 — The test suite is almost empty and not automated. [Verified]**
`tests/` holds five files, 139 lines in total. `test_chunker.py` has 0 lines (`wc -l`), `concurrent_providers.py` is a script rather than a test, and no workflow runs `pytest`. `bandit` is told to skip `tests`. The CI "hard gates" are lint, security lint, and the LLM-judge eval gate; ordinary logic is gated by nothing.

**F-05 — Import-time side effects block testing and fail-open design. [Verified]**
Importing `advanced_rag` constructs BM25 (raises `FileNotFoundError` if `chunks.json` is missing) and loads the reranker. A unit test cannot import the pipeline without a built index and model downloads.

**F-06 — Dependencies are not reproducible. [Verified]**
`requirements.txt` pins only `transformers` and `sentence-transformers`; torch is pinned in the Dockerfile. `langchain*`, `chromadb`, `fastapi`, `pydantic`, `groq` and others float, and there is no lockfile. Any rebuild can change behaviour. This also undermines eval comparability across time.

## B. Retrieval and evaluation

**F-07 — The corpus is too small to discriminate between pipeline variants. [Measured]**
40 chunks, 5 PDFs, one domain. `compare_report.txt` (n=37 dev pairs): reranked vs fused-top5 vs dense-only, success@5 0.865 / 0.892 / 0.919, every 98.3% CI spans zero. Dense-only is nominally best. At `TOP_K=5`, retrieval returns 12.5% of the corpus.

**F-08 — Held-out test split is 12 questions. [Measured]**
`golden_dataset.json`: 57 questions, 45 dev / 12 test. With 12 items a confidence interval is roughly ±0.3. The test split can detect only very large effects and should be used once, for final reporting.

**F-09 — BM25 tokenisation is naive. [Verified]**
`text.lower().split()` for documents and queries: punctuation stays attached, so "tyre?" and "tyre." do not match "tyre". The file's own docstring says to replace it for production. Effect on quality: unmeasured; trivially cheap to test in the harness.

**F-10 — Chunking has never been evaluated. [Verified / effect unmeasured]**
`CHUNK_SIZE=512` is *characters* (`length_function=len`). Mean chunk is 409 characters, roughly 90 tokens, against an embedder that accepts 512 tokens. The splitter runs per loaded `Document` (per PDF page), so no chunk spans a page boundary. Chunking is usually the highest-leverage retrieval parameter and is a fixed constant here.

**F-11 — No stage ablations and no no-retrieval baseline. [Verified absent]**
A `/query` can chain rewrite, retrieval, sufficiency judge, generation and citation verification: up to four serial LLM calls on a free tier. No experiment shows each stage earns its latency and quota. On a corpus this small, "put all 40 chunks in the prompt" is a baseline the pipeline has not been compared with.

**F-12 — The roadmap's Phase 13.0 status is stale. [Verified]**
It says "Q01 v2 format passed" and "in progress". The repo has 57 questions with categories, dev/test splits, `relevant` labels, a judge-calibration file and a paired-comparison report with confidence intervals. What is *not* established by the repo: that all 57 were manually validated, and what the judge's agreement with a human was.

**F-13 — An LLM judge gates CI. [Verified: CI runs the judge; calibration quality unverified]**
`eval-gate.yml` runs `eval.harness.judge` and `eval.harness.gate`. That spends Groq quota on every gated push and makes the gate subject to judge noise and rate limits. `judge_calibration.json` exists; the agreement it supports is not recorded anywhere I read.

**F-14 — Semantic cache design limits. [Verified]**
Key is `sha256(query)`, global; the stored fields are query, answer, provider. No prompt version, model, or corpus version in the key. The entity guard is `ENTITY_GROUPS = [{"sedan","suv","hatchback"}]` in `config.py`: a hard-coded, domain-specific heuristic that will not generalise to a bigger or different corpus. Phase 13.2 already plans prompt version in the namespace.

**F-15 — Ingest API vs loader mismatch. [Verified]**
`_resolve_and_validate_path` accepts only `.pdf`; `LOADER_MAP` handles `.pdf`, `.txt`, `.md`, `.docx`. The target corpus (confirmed by the owner, 2026-10-23) contains eight formats: PDF, DOCX, HTML, Markdown, CSV, XLS, XLSX, PPTX. HTML, CSV, XLS, XLSX and PPTX have no loader at all. The recursive character splitter is also unsuitable for tables (rows split mid-record, headers lost) and for slides. See F-28.

## C. Scaling to ~25 MB / 1,190 files

**F-16 — Impact on the current EC2 box (t3.small, 2 GiB, ~0.9 GiB used, swap in use). [Estimate]**
Yield from the existing files: 144 KB of PDF produced 16,351 characters (11%) in 40 chunks.

| If the 25 MB is… | Text | Chunks (~409 chars) | Extra RAM (BM25 ≈ 10 KB/chunk + HNSW ≈ 1.7 KB/chunk) | Verdict on current box |
|---|---|---|---|---|
| PDFs with the same text density as today | ~2.8 MB | ~7,000 | ~80 MB | Fine |
| PDFs with typical text density (30–60%) | 7–15 MB | ~18,000–37,000 | ~210–430 MB | Tight; swap thrash likely |
| Plain `.txt` / `.md` | ~25 MB | ~61,000 | ~700 MB | Does not fit alongside app + Redis + Prometheus |

Other effects:
- **Query latency:** BM25 scoring is O(N) per query but small next to the 3.5–4.6 s LLM time; the reranker only sees ~20 candidates. Expect tens of milliseconds added, not seconds.
- **Startup:** loading `chunks.json` and building BM25 for tens of thousands of chunks takes tens of seconds; the compose `start_period: 300s` already covers it.
- **Embedding on the instance:** bge-small on 2 burstable vCPUs is on the order of tens of chunks per second, so ~20,000 chunks is roughly 10–30 minutes of full CPU. That exhausts T3 CPU credits and starves live queries. T3 instances default to *unlimited* credit mode, which bills surplus CPU: a $0-budget risk. [Unverified: check the instance's credit specification in the console.]
- **Docker build:** because `scripts/ingest.py` runs inside `docker build`, every build in CI re-embeds the whole corpus and the index becomes an image layer re-pushed on each build and re-pulled onto the instance.
- **Disk:** index plus `chunks.json` of a few hundred MB fits easily; not a constraint.
- **Memory limits:** `docker-compose.prod.yml` sets no `mem_limit` on any service and no `maxmemory` on Redis, so one container can take the host down.

**Conclusion:** the instance can serve a corpus up to roughly 20–30k chunks if the index is built *off the box* and the BM25 footprint is measured; a 60k-chunk text corpus needs a different BM25 strategy or a larger host. The ingestion architecture (F-02, F-03) has to change before any of this.

**F-17 — Re-evaluation after growing the corpus. [Reasoned]**
The dataset does not have to be rewritten, but several things must be redone:
- Chunk IDs are `sha256(source::chunk_index)`, so existing chunk identities survive unless the existing PDFs are re-chunked. Re-chunking (F-10) invalidates `relevant` labels and evidence spans.
- Retrieval-only metrics must be **re-baselined** (cheap, no LLM). They should drop; that drop is the signal.
- All `unanswerable`, `adversarial` and `ambiguous` questions must be **re-audited**: new documents can make an unanswerable question answerable.
- The dataset needs **new questions** covering the new documents; the current 57 test one domain.
- Generation and judge runs need redoing only for the variants being compared.
- CI must not ingest the full corpus. Keep a small fixed fixture corpus for the CI gate and record a corpus-manifest hash in every eval run.

## D. Security and operations

**F-18 — Long-lived AWS keys in GitHub secrets. [Verified: `build-push.yml` uses `secrets.AWS_ACCESS_KEY_ID`; rotation reminder per `Memory.md`]**
GitHub OIDC to an IAM role removes stored keys, needs no budget, and removes the rotation chore.

**F-19 — Auth edge case. [Verified by reading; not run]**
`secrets.compare_digest(provided_key, os.getenv(config.API_KEY))`: if the env var is unset, `getenv` returns `None` and `compare_digest` raises `TypeError`, giving a 500 rather than a clean failure at startup. Single shared key; no per-user identity or document-level access control, although `Architecture.md`'s definition of done says "retrieve only authorized evidence".

**F-20 — No alerting, SLOs, load test, or documented backup/restore. [Verified absent in files read]**
`prometheus.yml` has a scrape config only: no `rule_files`, no Alertmanager. Latency is known from three live calls. The index is derivable from source documents, so "backup" can be a documented rebuild procedure — but it is not documented, and the source documents themselves live in git.

**F-21 — Privacy and exposure decision for personal documents. [Unverified: repo visibility not checked]**
A 1,190-file personal corpus behind a public HTTPS endpoint guarded by one key, plus request logs containing queries, needs an explicit decision: keep the corpus out of git (and out of any public repo), decide what the public demo indexes, and set log retention.

**F-22 — Dependency and image scanning absent. [Verified absent]**
`bandit` covers first-party code only. No `pip-audit`, Dependabot, or image scan.

## E. Process and documentation

**F-23 — Documentation drift. [Verified]**
Two copies of the roadmap (`docs/context/Roadmap.md`, `docs/architecture/roadmap.md`) differing by two lines. `README.md` and `docs/README.md` describe a "21-phase" roadmap; the roadmap has 16 phases. `Memory.md` §2 duplicates the Phase 13 plan and will diverge from the roadmap.

**F-24 — Roadmap lacks measurable exit criteria and dates. [Verified]**
Phases 1–10 say "Complete" with no recorded outcome. The new roadmap adds exit criteria for open phases; back-filling outcomes for Phases 1–10 is optional.

**F-25 — Repo hygiene. [Verified]**
Commented-out blocks in `api/routers/ingest.py`; typos in log messages ("Cache cleare failed aftrer ingest"); `eval/legacy/` and `experiments/` kept alongside live code; `ragas_library_eval.py` described as throwaway. Low priority, but it is the kind of thing reviewers notice, and `Ponytail.md` asks for the opposite.

**F-26 — Phase-order issues in the old roadmap. [Reasoned]**
Human feedback (the only source of real-world labels) sat behind a frontend; Graph/Multimodal RAG was planned before the base system had been scaled; "later tracks" contradicted the roadmap's own "solve a concrete problem" rule. Addressed in the revised roadmap.

## F. Added after follow-up questions (2026-10-23)

**F-27 — Two hand-synchronised stores are the root cause of F-01. [Verified]**
Chroma (persistent, embedded in the app process; its HNSW graph is loaded into RAM) and a BM25 index (purely in-memory, built from `chunks.json` at import) are kept consistent only by whichever script last wrote `chunks.json`. Chroma itself is not "in-memory", but the keyword index is, and nothing makes the two agree. A store that holds vectors, keyword index and metadata together (for example Postgres + pgvector, or SQLite FTS5 + `sqlite-vec`) removes this failure class instead of patching it. Phase 15.0 decides this with a measured bake-off. Pinecone and managed free-tier databases were considered and not shortlisted (privacy F-21, free-tier limits and pauses, no native BM25, network latency); figures quoted in the roadmap come from third-party summaries and must be re-verified before any decision depends on them.

**F-28 — Multi-format support is much larger than "add loaders". [Verified for the loader; the rest is reasoned]**
For PDF, DOCX, HTML, MD, CSV, XLS, XLSX and PPTX: five formats have no loader; tables need row-group chunking with repeated headers; slides need per-slide chunks; HTML needs boilerplate removal; legacy `.xls` needs a separate reader. Tabular files can dominate the chunk count (F-16). Retrieval cannot answer aggregation questions over tables, so the supported question types must be decided and the rest should abstain. Hidden sheets, notes, comments and HTML hidden elements are injection carriers and need a stated policy plus scanning (F-03). Office files are untrusted zip archives and need size and time limits. The `unstructured` dependency already in `requirements.txt` is heavy for a 2 GiB image; lighter per-format libraries should be compared. The 57-question golden dataset covers none of these content types. Owner Phase 15.1.
