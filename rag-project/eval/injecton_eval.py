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