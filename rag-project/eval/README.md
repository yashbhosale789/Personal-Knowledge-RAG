# eval

Run everything from `rag-project/` with `python -m` (needs the `.venv` and an ingested index).

## Layout

- `paths.py` - every file path used by the eval code.
- `data/` - golden dataset, judge calibration, injection cases (tracked inputs).
- `harness/` - generate, judge, gate, retrieval_eval, compare, store (the pipeline).
- `tools/` - dataset authoring: validate, split, candidates, review, probe.
- `security/` - prompt-injection and scanner evals, plus `injection_results.json`.
- `runs/` - generated outputs (gitignored).
- `legacy/` - retired scripts and datasets, kept untouched.

## Run order

| Step | Command | Reads | Writes |
|---|---|---|---|
| 1 | `python -m eval.tools.validate_dataset` | `data/golden_dataset.json`, `storage/chunks.json` | nothing |
| 2 | `python -m eval.harness.generate --variants baseline` | golden dataset, `runs/rewrites.json` | `runs/generations.jsonl`, `runs/rewrites.json` |
| 3 | `python -m eval.harness.judge --variants baseline` | `runs/generations.jsonl` | `runs/judgments.jsonl` |
| 4 | `python -m eval.harness.gate --variant baseline` | generations, judgments | nothing (exit 0 pass, 1 fail, 2 incomplete) |

Retrieval only:

- `python -m eval.harness.retrieval_eval` reads the golden dataset and `runs/rewrites.json`, writes `runs/retrieval_baseline_c1.json`. With `RAG_CORPUS=c2` it reads the c2 index and writes `runs/retrieval_baseline_c2.json`. `runs/retrieval_baseline.json` is the frozen pre-15.1 `c1` record (`9fc4650202`); nothing overwrites it.
- `python -m eval.tools.probe Q11 "query text"` prints the rank of Q11's evidence at each stage.
- Phase 15.2 variants (c2 only): `--split dev`, `--top-k`, `--pool` (first-stage depth), `--candidates` (reranker input), `--tokenizer split|word|word_s`, `--raw` (no rewrite) and `--out <file>`; each row also records `settings`, `context_chars` and `rerank_ms`. A chunking variant is selected with `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP` and `RAG_CHUNK_MERGE_PAGES=1`; build it with `scripts/ingest.py` under the same variables (own index `storage/chroma_c2_s<size>o<overlap>[m]`; refused without `RAG_CORPUS=c2`). `RAG_TOP_K` sets the chunks handed to generation (reranker output) the same way, c2 only; it is in the generation fingerprint.
- `python -m eval.tools.ann_check` compares Chroma's HNSW top-k with exact cosine on the dev items.
- `compare.py` also takes `--company <folder>`, `--brand` and `--metric-b` (e.g. a `TOP_K` 3 run's `recall@3` against the base's `recall@5`).

Every generation, judgment and retrieval record carries `dataset` and `corpus` ids (`store.run_ids()`). Dataset `v1` (`data/golden_dataset.json`) = `51bcd1e330` on corpus `c1` = `9fc4650202` (`2ef6192555` since the 15.1 text cleanup). Dataset `v2` (`data/golden_dataset_c2.json`, selected by `RAG_CORPUS=c2`) = `a831d87d09` on corpus `c2` = `80f20e0aa4`: v1 relabelled for c2 plus 22 questions from the upstream CSV (origin `upstream`). CI uses `v1` on `c1` only. The 12-question test split is frozen: final reporting only.

Comparing two runs: `python -m eval.harness.compare gen:baseline gen:other faithfulness`.

## Dataset authoring

`generate_candidates` writes `runs/candidates.jsonl`; `review_candidates` reads it, appends accepted items to the golden dataset and logs decisions in `runs/candidates_reviewed.jsonl`. `assign_split` refuses to run once a test split exists.

## Security

`python -m eval.security.scanner_eval` and `python -m eval.security.injection_eval` read `data/injection_cases.json`; the latter calls the LLM.

Calibrate the judge with `python -m eval.harness.judge --calibrate` (writes `data/judge_calibration.json`).
