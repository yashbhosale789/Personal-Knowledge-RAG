import json
import sys
import time
from hashlib import sha256

import config
from eval.paths import BASELINE_PATH as RESULTS_PATH
from eval.paths import GOLDEN_PATH as DEFAULT_DATASET
from eval.paths import REWRITES_PATH
from eval.tools.validate_dataset import basename, norm
from src.pipeline.advanced_rag import retrieve_context
from src.pipeline.query_rewriter import rewrite_query
from src.vectorstore.store import get_vectorstore

STAGE_KS = {
    "dense": (1, 5, 20),
    "bm25": (1, 5, 20),
    "fused": (1, 5, 10),
    "fused_top5": (1, 3, 5),
    "reranked": (1, 3, 5),
}

SLICE_KEYS = [
    ("dense", "recall@5"),
    ("bm25", "recall@5"),
    ("fused", "recall@10"),
    ("reranked", "recall@5"),
    ("reranked", "mrr"),
]


def chunk_source(chunk: dict) -> str:
    meta = chunk["metadata"]
    return basename(meta.get("filename") or meta.get("source", ""))


def match_matrix(item: dict, ranked: list[dict]) -> list[list[bool]]:
    cols = [(chunk_source(c), norm(c["text"])) for c in ranked]
    return [
        [src == rel["source"] and norm(rel["evidence"]) in text for src, text in cols]
        for rel in item["relevant"]
    ]


def score(item: dict, ranked: list[dict], ks: tuple[int, ...]) -> dict[str, float]:
    matrix = match_matrix(item, ranked)
    any_of = item.get("any_of", False)
    out: dict[str, float] = {}

    for k in ks:
        covered = [any(row[:k]) for row in matrix]
        out[f"recall@{k}"] = (
            float(any(covered)) if any_of else sum(covered) / len(covered)
        )
        out[f"success@{k}"] = float(any(covered) if any_of else all(covered))

    first = [row.index(True) + 1 for row in matrix if True in row]
    out["mrr"] = 1 / min(first) if first else 0.0
    return out


def load_rewrites() -> dict:
    sha = sha256(config.REWRITE_SYSTEM.encode()).hexdigest()[:8]
    if REWRITES_PATH.exists():
        cache = json.loads(REWRITES_PATH.read_text(encoding="utf-8"))
        if cache.get("prompt_sha") == sha:
            return cache
    return {"prompt_sha": sha, "rewrites": {}}


def get_rewrite(question: str, cache: dict) -> str:
    if question not in cache["rewrites"]:
        for attempt in range(3):
            try:
                cache["rewrites"][question] = rewrite_query(question)
                break
            except Exception as e:
                if "429" not in str(e) or attempt == 2:
                    raise
                time.sleep(60 * (attempt + 1))
        REWRITES_PATH.write_text(
            json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        time.sleep(3)
    return cache["rewrites"][question]


def mean(rows: list[dict], stage: str, metric: str) -> float:
    return sum(r["metrics"][stage][metric] for r in rows) / len(rows)


def report_all(rows: list[dict]) -> None:
    print(f"\nALL answerable questions (n={len(rows)})")
    for stage in STAGE_KS:
        cells = "  ".join(
            f"{m}={mean(rows, stage, m):.2f}" for m in rows[0]["metrics"][stage]
        )
        print(f"  {stage:<10} {cells}")


def report_slice(title: str, rows: list[dict]) -> None:
    if not rows:
        return
    cells = "  ".join(f"{s}.{m}={mean(rows, s, m):.2f}" for s, m in SLICE_KEYS)
    print(f"  {title:<16} n={len(rows):<3} {cells}")


def main() -> None:
    golden = json.loads(DEFAULT_DATASET.read_text(encoding="utf-8"))
    items = [i for i in golden if i["expected_outcome"] == "answer"]

    chunks_json = len(json.loads(config.CHUNKS_PATH.read_text(encoding="utf-8")))
    chroma = get_vectorstore()._collection.count()
    if chroma != chunks_json:
        sys.exit(
            f"index mismatch: Chroma {chroma} vs chunks.json {chunks_json}; re-ingest first"
        )

    cache = load_rewrites()
    rows = []
    for n, item in enumerate(items, 1):
        query = get_rewrite(item["question"], cache)
        stages = retrieve_context(query)
        stages["fused_top5"] = stages["fused"][:5]
        metrics = {
            stage: score(item, stages[stage], ks) for stage, ks in STAGE_KS.items()
        }

        rows.append(
            {
                "id": item["id"],
                "category": item["category"],
                "origin": item["origin"],
                "split": item["split"],
                "brand": "aventro" in item["question"].lower(),
                "query": query,
                "prompt_version": config.PROMPT_VERSION,
                "metrics": metrics,
            }
        )
        print(
            f"[{n}/{len(items)}] {item['id']} fused.recall@10={metrics['fused']['recall@10']:.2f} "
            f"reranked.recall@5={metrics['reranked']['recall@5']:.2f} mrr={metrics['reranked']['mrr']:.2f}"
        )
    RESULTS_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    report_all(rows)
    print("\nSLICES")
    for category in sorted({r["category"] for r in rows}):
        report_slice(category, [r for r in rows if r["category"] == category])
    for origin in ("manual", "synthetic"):
        report_slice(origin, [r for r in rows if r["origin"] == origin])
    report_slice("brand in query", [r for r in rows if r["brand"]])
    report_slice("no brand", [r for r in rows if not r["brand"]])


def _selfcheck() -> None:
    chunks = [
        {"metadata": {"source": "D:\\x\\a.pdf"}, "text": "foo"},
        {"metadata": {"filename": "a.pdf"}, "text": "The quick brown fox"},
    ]
    item = {
        "relevant": [
            {"source": "a.pdf", "evidence": "quick brown fox"},
            {"source": "a.pdf", "evidence": "absent span"},
        ]
    }
    result = score(item, chunks, (1, 2))
    assert result["recall@1"] == 0 and result["recall@2"] == 0.5  # nosec B101
    assert result["success@2"] == 0 and result["mrr"] == 0.5  # nosec B101
    assert score({**item, "any_of": True}, chunks, (2,))["recall@2"] == 1  # nosec B101


if __name__ == "__main__":
    _selfcheck()
    main()
