import json
import re
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent.parent))

from src.pipeline.advanced_rag import _build_prompt
from src.llm.client import call_llm
from config import SYSTEM_PROMPT


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
        "injection_succeded": hit,
        "answer": answer,
    }


