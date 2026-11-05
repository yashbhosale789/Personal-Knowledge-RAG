# Evaluation

Every quality claim in this project is measured on a versioned dataset against a versioned corpus, and every comparison is paired with a confidence interval. This page holds the method, the current numbers and how to reproduce them.

**Contents:** [Method](#method) · [Retrieval](#retrieval) · [End to end](#end-to-end) · [Retrieval tuning (Phase 15.2)](#retrieval-tuning-phase-152) · [CI regression gate](#ci-regression-gate) · [Security evals](#security-evals) · [Running it](#running-it)

---

## Method

| | `c1` / `v1` | `c2` / `v2` |
| --- | --- | --- |
| Corpus | 5 PDF car manuals, 40 chunks | 236 PDFs from 5 fictional companies ([RAG-Multi-Corpus](https://github.com/udayallu/RAG-Multi-Corpus), MIT), 2,221 chunks |
| Corpus id | `2ef6192555` | `80f20e0aa4` |
| Dataset | `eval/data/golden_dataset.json`, 57 questions (45 dev, 12 frozen test) | `eval/data/golden_dataset_c2.json`, 79 questions (v1 + 22 from the upstream query set), 71 answerable |
| Used by | CI and production | offline evaluation (`RAG_CORPUS=c2`) |

- **Question types:** normal, multi-hop, difficult, ambiguous, adversarial and unanswerable. Every answerable question has evidence spans that `validate_dataset` checks against the corpus.
- **Ids:** corpora, datasets and prompts are content-hashed, so a result always names exactly what produced it. The prompt version for the results below is `938331ced9a6`.
- **Statistics:** comparisons are paired on question id (`eval/harness/compare.py`): bootstrap 95% CI and a sign test. If the CI includes 0, the result is reported as not distinguishable.
- **Judge:** calibrated against hand-labelled good and bad answers (n = 20 per metric; AUC 1.0 for faithfulness, correctness and relevancy).
- **Test split:** the 12 test questions are frozen and are not used for tuning.

## Retrieval

Retrieval-only, no LLM judge calls (from `eval/runs/retrieval_baseline_*.json`):

| Run | n | Dense R@5 | BM25 R@5 | Fused R@10 | Reranked R@5 | Reranked MRR |
| --- | --- | --- | --- | --- | --- | --- |
| `c1` / `v1` | 46 | 0.91 | 0.81 | 0.97 | 0.90 | 0.82 |
| `c2` / `v2`, all | 71 | 0.77 | 0.66 | 0.85 | 0.81 | 0.72 |
| `c2` / `v2`, the 22 new questions | 22 | 0.73 | 0.59 | 0.75 | 0.75 | 0.65 |

Scaling the corpus 55× costs the first-stage retrievers about 0.09 recall@5 (paired on 46 shared questions: dense −0.087, 95% CI −0.174 to −0.022), and the reranker absorbs most of it (−0.033, CI includes 0).

## End to end

From the [failure analysis](docs/architecture/eval-failure-analysis-2026-10-28.md) on `c1` / `v1` dev (2026-10-28):

- **34 of 45** dev questions fully correct.
- **8 of 8** questions that should abstain did abstain, so no answer was given without support.
- Failure groups: over-abstention (4), ranking (2), retrieval misses (2), incomplete answers (2).

## Retrieval tuning (Phase 15.2)

On `c2` / `v2`, 61 answerable dev questions, each variant paired against the base (512/64, `TOP_K` 5: reranked R@5 0.820, MRR 0.721).

| Distinguishable | Not distinguishable |
| --- | --- |
| Chunk size 1024: better on reranked R@5 (+0.082), MRR (+0.111), dense and BM25 R@5 | Chroma HNSW vs exact search: identical top-5 and top-20 for 61/61 questions |
| Chunk size 256 at either overlap, even at equal context: worse | Merging pages before chunking |
| Overlap 128 at 512: recall worse | `TOP_K` 8; rerank pool 20 or 40 |
| `TOP_K` 3 on 512 chunks: worse | BM25 tokenizer `\w+` (helps BM25 alone, no change after fusion and rerank) |
| 1024/64 at `TOP_K` 3 vs base: MRR +0.104 (recall +0.066, sign test p 0.06) | Skipping the query rewrite, retrieval only |

**Chosen for `c2`:** chunk size 1024, overlap 64, `TOP_K` 3. It hands generation about the same context as today (2,380 vs 2,262 characters), so the gain is not from extra context. It is not shipped to production or CI yet. Stage ablations (no rewrite, no sufficiency judge, no verifier) are in progress. Full tables: [roadmap, Phase 15.2](docs/architecture/roadmap.md#phase-152--retrieval-tuning-and-stage-ablations).

## CI regression gate

`.github/workflows/eval-gate.yml` runs an LLM-judge gate on 4 CI questions (faithfulness ≥ 0.85, relevancy ≥ 0.75) when pipeline code, config, data or the harness change, weekly, and on demand. A real regression fails it. A run cut short by free-tier rate limits is reported as a warning, not a failure.

## Security evals

- `eval/security/injection_eval.py`: prompt-injection resistance of the full pipeline.
- `eval/security/scanner_eval.py`: the ingest-time injection scanner. INJ01–03 are caught; INJ04 is a known miss, and the prompt boundary remains the main defence.

## Running it

From `rag-project/`, with the `.venv` active and an ingested index. Prefix with `RAG_CORPUS=c2` for the full corpus.

```powershell
python -m eval.tools.validate_dataset      # dataset schema and evidence spans, no LLM calls
python -m eval.harness.retrieval_eval      # retrieval metrics, no judge calls
python -m eval.harness.generate            # answers for the golden dataset (LLM calls)
python -m eval.harness.judge               # LLM-judge scores
python -m eval.harness.gate                # regression gate
python -m eval.harness.compare gen:baseline gen:other faithfulness   # paired comparison
python -m eval.tools.ann_check             # HNSW vs exact search
python -m eval.security.injection_eval     # prompt-injection resistance
```

`generate` and `judge` write to `eval/runs/` and resume completed cases. All providers are on free tiers, so check the call count before a full run. Run order, dataset authoring and tools: [`rag-project/eval/README.md`](rag-project/eval/README.md).
