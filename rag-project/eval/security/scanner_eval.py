import json

from eval.paths import INJECTION_CASES_PATH as CASES_PATH
from src.pipeline.injection_scanner import scan_for_injection


def main():
    with open(CASES_PATH) as f:
        cases = json.load(f)

    for case in cases:
        full_text = "\n".join(c["text"] for c in case["contexts"])
        result = scan_for_injection(full_text)
        status = "CAUGHT" if result["flagged"] else "MISSEED"
        print(f"{case['id']} ({case['category']}): {status} - {result['categories']}")


if __name__ == "__main__":
    main()
