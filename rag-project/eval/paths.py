from pathlib import Path

EVAL_DIR = Path(__file__).parent
ROOT = EVAL_DIR.parent
DATA_DIR = EVAL_DIR / "data"
RUNS_DIR = EVAL_DIR / "runs"
SECURITY_DIR = EVAL_DIR / "security"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

GOLDEN_PATH = DATA_DIR / "golden_dataset.json"
CALIBRATION_PATH = DATA_DIR / "judge_calibration.json"
INJECTION_CASES_PATH = DATA_DIR / "injection_cases.json"

GEN_PATH = RUNS_DIR / "generations.jsonl"
JUDGE_PATH = RUNS_DIR / "judgments.jsonl"
REWRITES_PATH = RUNS_DIR / "rewrites.json"
BASELINE_PATH = RUNS_DIR / "retrieval_baseline.json"
CANDIDATES_PATH = RUNS_DIR / "candidates.jsonl"
REVIEWED_PATH = RUNS_DIR / "candidates_reviewed.jsonl"

INJECTION_RESULTS_PATH = SECURITY_DIR / "injection_results.json"
