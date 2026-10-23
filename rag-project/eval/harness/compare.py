import argparse
import json
import random
from math import comb

from eval.harness import store
from eval.paths import GEN_PATH, JUDGE_PATH, RUNS_DIR
from eval.paths import GOLDEN_PATH as DEFAULT_DATASET


def load_ret(stage: str, filename: str) -> dict[str, dict[str, float]]:
    rows = json.loads((RUNS_DIR / filename).read_text(encoding="utf-8"))
    return {r["id"]: r["metrics"][stage] for r in rows}


def load_gen(variant: str, fp: str, golden: dict) -> dict[str, dict[str, float]]:
    gens, judged = store.load(GEN_PATH), store.load(JUDGE_PATH)
    rows: dict[str, dict[str, float]] = {}
    for qid, item in golden.items():
        gen = gens.get(store.key(variant, qid, fp))
        if gen is None or "error" in gen:
            continue
        refusal_expected = item["expected_outcome"] == "abstain"
        row = {
            "behavior": float(gen["refused"] == refusal_expected),
            "latency_ms": float(gen["latency_ms"]),
        }
        for metric in ("faithfulness", "correctness", "relevancy"):
            record = judged.get(f"{gen['key']}|{metric}")
            if record is not None and record["score"] is not None:
                row[metric] = record["score"]
        rows[qid] = row
    return rows


def load(spec: str, golden: dict) -> dict[str, dict[str, float]]:
    kind, _, rest = spec.partition(":")
    name, _, extra = rest.partition("@")
    if kind == "ret":
        return load_ret(name, extra or "retrieval_baseline.json")
    if kind == "gen":
        return load_gen(name, extra or store.fingerprint(), golden)
    raise SystemExit(
        f"bad spec {spec!r}: use ret:<stage>[@file] or gen:<variant>[@fingerprint]"
    )


def sign_test(wins: int, losses: int) -> float:
    n = wins + losses
    tail = sum(comb(n, k) for k in range(min(wins, losses) + 1)) / 2**n if n else 1.0
    return min(1.0, 2 * tail)


def bootstrap_ci(
    diffs: list[float], alpha: float, reps: int = 10_000, seed: int = 0
) -> tuple[float, float]:
    rng = random.Random(seed)  # nosec B311
    means = sorted(
        sum(rng.choices(diffs, k=len(diffs))) / len(diffs) for _ in range(reps)
    )
    return means[int(alpha / 2 * reps)], means[int((1 - alpha / 2) * reps) - 1]


def verdict(
    diffs: list[float],
    p: float,
    low: float,
    high: float,
    alpha: float,
    min_effect: float,
) -> str:
    mean = sum(diffs) / len(diffs)
    if p >= alpha or low <= 0 <= high:
        return "no evidence of a difference at this sample size"
    if abs(mean) < min_effect:
        return f"significant but smaller than the minimum useful effect ({min_effect})"
    return "A higher" if mean > 0 else "B higher"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("metric")
    p.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    p.add_argument(
        "--family",
        type=int,
        default=1,
        help="number of comparisons in this family (Bonferroni)",
    )
    p.add_argument(
        "--min-effect",
        type=float,
        default=0.0,
        help="smallest difference worth acting on",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    golden = {
        i["id"]: i for i in json.loads(DEFAULT_DATASET.read_text(encoding="utf-8"))
    }
    a, b = load(args.a, golden), load(args.b, golden)

    def in_split(qid: str) -> bool:
        return args.split in ("all", golden[qid]["split"])

    sa, sb = {q for q in a if in_split(q)}, {q for q in b if in_split(q)}
    ids = sorted(
        (q for q in sa & sb if args.metric in a[q] and args.metric in b[q]),
        key=lambda q: int(q[1:]),
    )
    if len(ids) < 2:
        raise SystemExit(
            f"only {len(ids)} paired questions with metric {args.metric!r}; nothing to compare"
        )

    diffs = [a[q][args.metric] - b[q][args.metric] for q in ids]
    alpha = 0.05 / args.family
    wins, losses = sum(d > 0 for d in diffs), sum(d < 0 for d in diffs)
    p = sign_test(wins, losses)
    low, high = bootstrap_ci(diffs, alpha)
    mean_diff = sum(diffs) / len(diffs)

    print(f"A={args.a}  B={args.b}  metric={args.metric}  split={args.split}")
    print(
        f"  pairs={len(ids)}  in both runs={len(sa & sb)}  only A={len(sa - sb)}  only B={len(sb - sa)}"
    )
    print(
        f"  mean A={sum(a[q][args.metric] for q in ids) / len(ids):.3f}  B={sum(b[q][args.metric] for q in ids) / len(ids):.3f}"
    )
    print(
        f"  diff A-B = {mean_diff:+.3f}   {100 * (1 - alpha):.1f}% CI [{low:+.3f}, {high:+.3f}]"
    )
    print(
        f"  A higher on {wins}, B higher on {losses}, tied {len(ids) - wins - losses}; sign test p={p:.4f} (alpha {alpha:.4f})"
    )
    print(f"  verdict: {verdict(diffs, p, low, high, alpha, args.min_effect)}")
    for q, d in sorted(zip(ids, diffs), key=lambda t: -abs(t[1]))[:20]:
        if d:
            print(f"    {q}: A={a[q][args.metric]:.2f}  B={b[q][args.metric]:.2f}")


def _selfcheck() -> None:
    assert (
        abs(sign_test(8, 1) - 0.0390625) < 1e-9 and sign_test(0, 0) == 1.0
    )  # nosec B101
    assert bootstrap_ci([0.5] * 10, 0.05) == (0.5, 0.5)  # nosec B101
    assert verdict([0.0] * 10, 1.0, 0.0, 0.0, 0.05, 0.0).startswith(
        "no evidence"
    )  # nosec B101
    assert (
        verdict([1.0] * 10, sign_test(10, 0), 1.0, 1.0, 0.05, 0.0) == "A higher"
    )  # nosec B101
    assert "smaller" in verdict(
        [0.1] * 10, sign_test(10, 0), 0.1, 0.1, 0.05, 0.5
    )  # nosec B101


if __name__ == "__main__":
    _selfcheck()
    main()
