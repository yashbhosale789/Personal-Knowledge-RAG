import json
import sys
from pathlib import Path

SCORES_PATH = Path(__file__).parent / "ragas_scores.json"
FAITHFULLNESS_FLOOR = 0.85
ANSWER_RELEVANCY_FLOOR = 0.75

scores = json.load(open(SCORES_PATH))

faithfullness_avg = sum(s["faithfullness"] for s in scores) / len(scores)
ar_values = [
    s["answer_relevancy"]
    for s in scores
    if s["answer_relevancy"] == s["answer_relevancy"]
]
ar_avg = sum(ar_values) / len(ar_values) if ar_values else 1.0

print(f"Faithfulness={faithfullness_avg:.4f} (floor {FAITHFULLNESS_FLOOR})")
print(f"answer_relevancy={ar_avg:.4f} (floor {ANSWER_RELEVANCY_FLOOR})")

if faithfullness_avg < FAITHFULLNESS_FLOOR or ar_avg < ANSWER_RELEVANCY_FLOOR:
    print("REFRESSION - below floor")
    sys.exit(1)

print("PASS")
