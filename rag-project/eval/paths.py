from pathlib import Path

import config

EVAL_DIR = Path(__file__).parent
ROOT = EVAL_DIR.parent
DATA_DIR = EVAL_DIR / "data"
RUNS_DIR = EVAL_DIR / "runs"
SECURITY_DIR = EVAL_DIR / "security"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

# Dataset v1 (corpus c1, CI) and v2 (corpus c2, 15.1): v2's labels cite c2-only files.
GOLDEN_PATH = DATA_DIR / (
    "golden_dataset_c2.json" if config.CORPUS == "c2" else "golden_dataset.json"
)
CALIBRATION_PATH = DATA_DIR / "judge_calibration.json"
INJECTION_CASES_PATH = DATA_DIR / "injection_cases.json"

GEN_PATH = RUNS_DIR / "generations.jsonl"
JUDGE_PATH = RUNS_DIR / "judgments.jsonl"
REWRITES_PATH = RUNS_DIR / "rewrites.json"
# One file per corpus (RAG_CORPUS). retrieval_baseline.json is the frozen c1 record from
# before 15.1 (corpus 9fc4650202); nothing writes it any more.
BASELINE_PATH = RUNS_DIR / f"retrieval_baseline_{config.CORPUS}.json"
CANDIDATES_PATH = RUNS_DIR / "candidates.jsonl"
REVIEWED_PATH = RUNS_DIR / "candidates_reviewed.jsonl"

INJECTION_RESULTS_PATH = SECURITY_DIR / "injection_results.json"
