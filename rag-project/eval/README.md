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

- `python -m eval.harness.retrieval_eval` reads the golden dataset and `runs/rewrites.json`, writes `runs/retrieval_baseline.json`.
- `python -m eval.tools.probe Q11 "query text"` prints the rank of Q11's evidence at each stage.

Every generation, judgment and retrieval record carries `dataset` and `corpus` ids (`store.run_ids()`). Dataset `v1` = `51bcd1e330` on corpus `c1` = `9fc4650202`. The 12-question test split is frozen: final reporting only.

Comparing two runs: `python -m eval.harness.compare gen:baseline gen:other faithfulness`.

## Dataset authoring

`generate_candidates` writes `runs/candidates.jsonl`; `review_candidates` reads it, appends accepted items to the golden dataset and logs decisions in `runs/candidates_reviewed.jsonl`. `assign_split` refuses to run once a test split exists.

## Security

`python -m eval.security.scanner_eval` and `python -m eval.security.injection_eval` read `data/injection_cases.json`; the latter calls the LLM.

Calibrate the judge with `python -m eval.harness.judge --calibrate` (writes `data/judge_calibration.json`).
