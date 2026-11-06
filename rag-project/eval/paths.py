from pathlib import Path

import config

EVAL_DIR = Path(__file__).parent
ROOT = EVAL_DIR.parent
DATA_DIR = EVAL_DIR / "data"
RUNS_DIR = EVAL_DIR / "runs"
SECURITY_DIR = EVAL_DIR / "security"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

# Dataset v2 (15.1, 79 questions; a superset of v1, which is in eval/legacy/).
GOLDEN_PATH = DATA_DIR / "golden_dataset.json"
CALIBRATION_PATH = DATA_DIR / "judge_calibration.json"
# PDF name -> company (the upstream folder; the corpus is flat since 15.2), for compare --company.
SOURCE_COMPANY_PATH = DATA_DIR / "source_company.json"
INJECTION_CASES_PATH = DATA_DIR / "injection_cases.json"

GEN_PATH = RUNS_DIR / "generations.jsonl"
JUDGE_PATH = RUNS_DIR / "judgments.jsonl"
REWRITES_PATH = RUNS_DIR / "rewrites.json"
# The current corpus and chunking (a chunking experiment gets its own file). Frozen history,
# never written: retrieval_baseline.json (c1 before 15.1), _c1.json and _c2.json (15.1).
BASELINE_PATH = RUNS_DIR / f"retrieval_baseline_current{config.INDEX_VARIANT}.json"
CANDIDATES_PATH = RUNS_DIR / "candidates.jsonl"
REVIEWED_PATH = RUNS_DIR / "candidates_reviewed.jsonl"

INJECTION_RESULTS_PATH = SECURITY_DIR / "injection_results.json"
