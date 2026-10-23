import json
import sys
from pathlib import Path

SCORES_PATH = Path(__file__).parent / "ragas_scores.json"
FAITHFULNESS_FLOOR = 0.85
ANSWER_RELEVANCY_FLOOR = 0.75

with open(SCORES_PATH) as f:
    scores = json.load(f)

faith_values = [s["faithfulness"] for s in scores if s.get("outcome") != "abstain"]
faithfulness_avg = sum(faith_values) / len(faith_values) if faith_values else 1.0

ar_values = [
    s["answer_relevancy"]
    for s in scores
    if s["answer_relevancy"] == s["answer_relevancy"]
]
ar_avg = sum(ar_values) / len(ar_values) if ar_values else 1.0

print(f"Faithfulness={faithfulness_avg:.4f} (floor {FAITHFULNESS_FLOOR})")
print(f"answer_relevancy={ar_avg:.4f} (floor {ANSWER_RELEVANCY_FLOOR})")

failed = faithfulness_avg < FAITHFULNESS_FLOOR or ar_avg < ANSWER_RELEVANCY_FLOOR

abstention_failures = [
    s["id"] for s in scores if s.get("expect_abstain") and s.get("outcome") != "abstain"
]
if abstention_failures:
    print(
        f"ABSTENTION CHECK FAILED — expected abstain but got an answer: {abstention_failures}"
    )
    failed = True
else:
    print("Abstention check: PASS")

if failed:
    print("REFRESSION - below floor")
    sys.exit(1)

print("PASS")
