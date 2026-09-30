import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SYSTEM_PROMPT
from src.llm.client import call_llm
from src.pipeline.advanced_rag import _build_prompt

CASE_PATH = Path(__file__).parent / "injection_cases.json"
RESULTS_PATH = Path(__file__).parent / "injection_results.json"


def load_cases() -> list[dict]:
    with open(CASE_PATH) as f:
        return json.load(f)


def run_case(case: dict) -> dict:
    prompt = _build_prompt(case["query"], case["contexts"])
    answer = call_llm(prompt, system=SYSTEM_PROMPT)

    hit = case["canary"] in answer

    return {
        "id": case["id"],
        "category": case["category"],
        "canary": case["canary"],
        "injection_succeeded": hit,
        "answer": answer,
    }


def main():
    cases = load_cases()
    print(f"Running {len(cases)} injuection cases...\n")

    results = [run_case(c) for c in cases]

    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    succeeded = [r for r in results if r["injection_succeeded"]]
    print(
        f"{len(succeeded)}/{len(results)} injection succeeded (defence FAILED on these):\n"
    )
    for r in succeeded:
        print(f"  [{r['category']}] {r['id']}")

    print(f"\nFull results -> {RESULTS_PATH}")


if __name__ == "__main__":
    main()
