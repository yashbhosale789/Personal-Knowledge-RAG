# Evaluation

Every quality claim in this project is measured on a versioned dataset against a versioned corpus, and every comparison is paired with a confidence interval. This page holds the method, the current numbers and how to reproduce them.

**Contents:** [Method](#method) · [Retrieval](#retrieval) · [End to end](#end-to-end) · [Retrieval tuning (Phase 15.2)](#retrieval-tuning-phase-152) · [CI regression gate](#ci-regression-gate) · [Security evals](#security-evals) · [Running it](#running-it)

---

## Method

One corpus and one dataset since 2026-11-06, used by CI, production and offline evaluation:

| | |
| --- | --- |
| Corpus | 236 PDFs from 5 fictional companies ([RAG-Multi-Corpus](https://github.com/udayallu/RAG-Multi-Corpus), MIT) in `data/documents/`, 1,295 chunks at 1024/64 |
| Corpus id | `281db7190c` |
| Dataset | `eval/data/golden_dataset.json` (v2, `8f89d42be9` (since 2026-11-06: `a831d87d09` with the CI flag moved from Q13 to Q12; questions and labels unchanged, so 15.2 results on `a831d87d09` still apply)): 79 questions, 71 answerable; 67 dev, 12 frozen test |

Earlier results name two corpora: `c1`, the 5 car-manual PDFs (now part of the corpus; id `2ef6192555`, dataset v1 `51bcd1e330`, kept in `eval/legacy/golden_dataset_v1.json`), and `c2`, the same 236 PDFs at 512/64 (`80f20e0aa4`).

- **Question types:** normal, multi-hop, difficult, ambiguous, adversarial and unanswerable. Every answerable question has evidence spans that `validate_dataset` checks against the corpus.
- **Ids:** corpora, datasets and prompts are content-hashed, so a result always names exactly what produced it. The prompt version for the results below is `938331ced9a6`.
- **Statistics:** comparisons are paired on question id (`eval/harness/compare.py`): bootstrap 95% CI and a sign test. If the CI includes 0, the result is reported as not distinguishable.
- **Judge:** calibrated against hand-labelled good and bad answers (n = 20 per metric; AUC 1.0 for faithfulness, correctness and relevancy).
- **Test split:** the 12 test questions are frozen and are not used for tuning.

## Retrieval

Retrieval-only, no LLM judge calls (from `eval/runs/retrieval_baseline_*.json`):

| Run | n | Dense R@5 | BM25 R@5 | Fused R@10 | Reranked R@k | Reranked MRR |
| --- | --- | --- | --- | --- | --- | --- |
| **Current** (1024/64, `TOP_K` 3), all | 71 | 0.91 | 0.79 | 0.91 | **0.88** (R@3) | **0.83** |
| `c1` / `v1` (history) | 46 | 0.91 | 0.81 | 0.97 | 0.90 (R@5) | 0.82 |
| `c2` / `v2` at 512/64, `TOP_K` 5, all | 71 | 0.77 | 0.66 | 0.85 | 0.81 (R@5) | 0.72 |
| `c2` / `v2` at 512/64, the 22 new questions | 22 | 0.73 | 0.59 | 0.75 | 0.75 (R@5) | 0.65 |

Scaling the corpus 55× costs the first-stage retrievers about 0.09 recall@5 (paired on 46 shared questions: dense −0.087, 95% CI −0.174 to −0.022), and the reranker absorbs most of it (−0.033, CI includes 0).

## End to end

Current configuration, dev split (Phase 15.2, 2026-11-06; 67 questions):

- **38 of 61** answerable questions fully correct (judge correctness 1.0); 51 answered, 10 refused.
- **5 of 6** questions that should abstain did abstain.

History, from the [failure analysis](docs/architecture/eval-failure-analysis-2026-10-28.md) on `c1` / `v1` dev (2026-10-28):

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

**Chosen and shipped (2026-11-06):** chunk size 1024, overlap 64, `TOP_K` 3. It hands generation about the same context as before (2,380 vs 2,262 characters), so the gain is not from extra context. The test split, used once, moves the same way (not distinguishable at n = 12). **Stage ablations** (no rewrite, no sufficiency judge, no citation verifier, rewrite only for short questions): none is distinguishable on any judged metric. The owner kept all four stages, so the architecture is unchanged. Full tables: [roadmap, Phase 15.2](docs/architecture/roadmap.md#phase-152--retrieval-tuning-and-stage-ablations).

## CI regression gate

`.github/workflows/eval-gate.yml` runs an LLM-judge gate on 4 CI questions (Q01, Q06, Q09, Q12) (faithfulness ≥ 0.85, relevancy ≥ 0.75) when pipeline code, config, data or the harness change, weekly, and on demand. A real regression fails it. A run cut short by free-tier rate limits is reported as a warning, not a failure.

## Security evals

- `eval/security/injection_eval.py`: prompt-injection resistance of the full pipeline.
- `eval/security/scanner_eval.py`: the ingest-time injection scanner. INJ01–03 are caught; INJ04 is a known miss, and the prompt boundary remains the main defence.

## Running it

From `rag-project/`, with the `.venv` active and an ingested index.

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
