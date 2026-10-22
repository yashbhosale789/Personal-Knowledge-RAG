import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import store
from judge import GEN_PATH, JUDGE_PATH
from validate_dataset import DEFAULT_DATASET

FAITHFULNESS_FLOOR = 0.85
RELEVANCY_FLOOR = 0.75


def evaluate(items, gens, judged, variant, fp, faith_floor, rel_floor):
    problems: list[str] = []
    failures: list[str] = []
    scores: dict[str, list[float]] = {
        "faithfulness": [],
        "relevancy": [],
        "correctness": [],
    }
    for item in items:
        gen = gens.get(store.key(variant, item["id"], fp))
        if gen is None or "error" in gen:
            problems.append(
                f"{item['id']}: no generation for variant {variant!r} at fingerprint {fp}"
            )
            continue

        wants_refusal = item["expected_outcome"] == "abstain"
        if gen["refused"] != wants_refusal:
            expected = "a refusal" if wants_refusal else "an answer"
            failures.append(
                f"{item['id']}: expected {expected} but the pipeline {'refused' if gen['refused'] else 'answered'}"
            )
        if gen["refused"]:
            continue

        for metric, value in scores.items():
            if metric == "correctness" and item["expected_outcome"] != "answer":
                continue
            record = judged.get(f"{gen['key']}|{metric}")
            if record is None or record["score"] is None:
                problems.append(f"{item['id']}: {metric} not judged")
            else:
                value.append(record["score"])

    means = {m: sum(v) / len(v) for m, v in scores.items() if v}
    for metric, floor in (("faithfulness", faith_floor), ("relevancy", rel_floor)):
        if metric in means and means[metric] < floor:
            failures.append(
                f"{metric} mean {means[metric]:.3f} is below the floor {floor}"
            )
    if not problems and "faithfulness" not in means:
        failures.append("no answered CI item was scored")
    return problems, failures, means


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--variant", default="ci")
    p.add_argument("--fp", default="", help="fingerprint to check; default = current")
    p.add_argument("--faith-floor", type=float, default=FAITHFULNESS_FLOOR)
    p.add_argument("--rel-floor", type=float, default=RELEVANCY_FLOOR)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    fp = args.fp or store.fingerprint()
    items = [
        i for i in json.loads(DEFAULT_DATASET.read_text(encoding="utf-8")) if i["ci"]
    ]
    problems, failures, means = evaluate(
        items,
        store.load(GEN_PATH),
        store.load(JUDGE_PATH),
        args.variant,
        fp,
        args.faith_floor,
        args.rel_floor,
    )
    print(f"gate: variant {args.variant!r}, fingerprint {fp}, {len(items)} CI items")
    floors = {
        "faithfulness": f"floor {args.faith_floor}",
        "relevancy": f"floor {args.rel_floor}",
        "correctness": "report only",
    }
    for metric, value in means.items():
        print(f"  {metric:<13} mean={value:.3f} ({floors[metric]})")
    for message in failures:
        print("REGRESSION:", message)
    for message in problems:
        print("INCOMPLETE:", message)
    print("FAIL" if failures else "INCOMPLETE" if problems else "PASS")
    return 1 if failures else 2 if problems else 0


def _selfcheck() -> None:
    items = [
        {"id": "A", "expected_outcome": "answer"},
        {"id": "B", "expected_outcome": "abstain"},
    ]
    gens = {
        "v|A|f": {"key": "v|A|f", "refused": False},
        "v|B|f": {"key": "v|B|f", "refused": True},
    }
    judged = {
        f"v|A|f|{m}": {"score": s}
        for m, s in (("faithfulness", 1.0), ("relevancy", 0.9), ("correctness", 1.0))
    }
    assert evaluate(items, gens, judged, "v", "f", 0.85, 0.75)[:2] == (
        [],
        [],
    )  # nosec B101
    assert evaluate(items, gens, judged, "v", "f", 1.01, 0.75)[1]  # nosec B101
    refused = {**gens, "v|A|f": {"key": "v|A|f", "refused": True}}
    assert evaluate(items, refused, judged, "v", "f", 0.85, 0.75)[1]  # nosec B101
    assert evaluate(items, {}, judged, "v", "f", 0.85, 0.75)[0]  # nosec B101


if __name__ == "__main__":
    _selfcheck()
    sys.exit(main())
