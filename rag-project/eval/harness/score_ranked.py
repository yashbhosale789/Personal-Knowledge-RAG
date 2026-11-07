"""Score another project's ranked retrieval with this harness (Phase 16.0 RAG variants).

A variant runs its own retrieval and writes a dump (its own code cannot share a process with
this app: both have top-level `config` and `src`):
    {"variant", "corpus", "settings",
     "results": {qid: {"query", "stages": {stage: [{"text", "metadata": {"source", "page"}}]}}}}
This scores every stage with retrieval_eval.score() and writes eval/runs/<out> in
retrieval_eval's row format, so compare.py reads it as ret:<stage>@<out>.
shortcut: file hand-off instead of an adapter interface; the 16.4 eval kit replaces it.

Usage (from rag-project/): python -m eval.harness.score_ranked <dump.json> --out <file>
"""

import argparse
import json
from pathlib import Path

from eval.harness import store
from eval.harness.retrieval_eval import STAGE_KS, mean, score
from eval.paths import GOLDEN_PATH, RUNS_DIR


def stage_ks(stage: str, depth: int) -> tuple[int, ...]:
    """recall@1/3/5 for every stage, plus the harness's deeper k where the list is that long."""
    return tuple(sorted({1, 3, 5} | {k for k in STAGE_KS.get(stage, ()) if k <= depth}))


def score_dump(dump: dict, golden: list[dict], dataset_id: str) -> list[dict]:
    items = [i for i in golden if i["expected_outcome"] == "answer"]
    results = dump["results"]
    missing = [i["id"] for i in items if i["id"] not in results]
    if missing:
        raise SystemExit(
            f"dump lacks {len(missing)} answerable items, e.g. {missing[:5]}"
        )
    stages = results[items[0]["id"]]["stages"]
    depth = {s: max(len(results[i["id"]]["stages"][s]) for i in items) for s in stages}
    return [
        {
            "id": item["id"],
            "category": item["category"],
            "origin": item["origin"],
            "split": item["split"],
            "query": results[item["id"]]["query"],
            "variant": dump["variant"],
            "dataset": dataset_id,
            "corpus": dump["corpus"],
            "settings": dump["settings"],
            "metrics": {
                s: score(item, results[item["id"]]["stages"][s], stage_ks(s, depth[s]))
                for s in stages
            },
        }
        for item in items
    ]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("dump", type=Path)
    p.add_argument("--out", required=True, help="file name in eval/runs")
    args = p.parse_args()
    dump = json.loads(args.dump.read_text(encoding="utf-8"))
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    rows = score_dump(dump, golden, store.content_id(GOLDEN_PATH))
    (RUNS_DIR / args.out).write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"{args.out}: {dump['variant']} corpus {dump['corpus']} {dump['settings']}")
    print(f"ALL answerable questions (n={len(rows)})")
    for stage, metrics in rows[0]["metrics"].items():
        cells = "  ".join(f"{m}={mean(rows, stage, m):.2f}" for m in metrics)
        print(f"  {stage:<10} {cells}")


if __name__ == "__main__":
    main()
