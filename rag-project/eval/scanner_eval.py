import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.injection_scanner import scan_for_injection

CASES_PATH = Path(__file__).parent / "injection_cases.json"


def main():
    with open(CASES_PATH) as f:
        cases = json.load(f)

    for case in cases:
        full_text = "\n".join(c["text"] for c in case["context"])
        result = scan_for_injection(full_text)
        status = "CAUGHT" if result["flagged"] else "MISSEED"
        print(f"{case[id]} ({case['category']}): {status} - {result['categories']}")


if __name__ == "__main__":
    main()