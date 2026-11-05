import argparse
import json
import re
import sys
import time
from hashlib import sha256

import config
from eval.harness import store
from eval.paths import BASELINE_PATH as RESULTS_PATH
from eval.paths import GOLDEN_PATH as DEFAULT_DATASET
from eval.paths import REWRITES_PATH, RUNS_DIR
from eval.tools.validate_dataset import basename, norm
from src.observability import track
from src.pipeline.advanced_rag import retrieve_context
from src.pipeline.query_rewriter import rewrite_query
from src.retrieval.bm25_retriever import BM25Retriever, tokenize
from src.retrieval.reranker import CrossEncoderReranker
from src.vectorstore.store import get_vectorstore

STAGE_KS = {
    "dense": (1, 5, 20),
    "bm25": (1, 5, 20),
    "fused": (1, 5, 10),
    "fused_top5": (1, 3, 5),
    "reranked": (1, 3, 5),
}


def word_tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def word_tokens_s(text: str) -> list[str]:
    # shortcut: naive plural strip (no stemmer installed); use a real stemmer if this ships
    return [
        w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
        for w in word_tokens(text)
    ]


# BM25 tokenizers compared in 15.2 (F-09); "split" is the one in production.
TOKENIZERS = {"split": tokenize, "word": word_tokens, "word_s": word_tokens_s}

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
    for stage in rows[0]["metrics"]:
        cells = "  ".join(
            f"{m}={mean(rows, stage, m):.2f}" for m in rows[0]["metrics"][stage]
        )
        print(f"  {stage:<10} {cells}")


def report_slice(title: str, rows: list[dict]) -> None:
    if not rows:
        return
    cells = "  ".join(f"{s}.{m}={mean(rows, s, m):.2f}" for s, m in SLICE_KEYS)
    print(f"  {title:<16} n={len(rows):<3} {cells}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Retrieval-only eval; flags are 15.2 variants"
    )
    p.add_argument("--split", choices=["all", "dev"], default="all")
    p.add_argument(
        "--top-k", type=int, default=config.TOP_K, help="chunks to generation"
    )
    p.add_argument("--pool", type=int, help="first-stage depth (default top-k * 4)")
    p.add_argument("--candidates", type=int, help="reranker input (default top-k * 2)")
    p.add_argument("--tokenizer", choices=sorted(TOKENIZERS), default="split")
    p.add_argument(
        "--raw", action="store_true", help="query with the question, no rewrite"
    )
    p.add_argument(
        "--out", help=f"file name in eval/runs (default {RESULTS_PATH.name})"
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    golden = json.loads(DEFAULT_DATASET.read_text(encoding="utf-8"))
    items = [
        i
        for i in golden
        if i["expected_outcome"] == "answer" and args.split in ("all", i["split"])
    ]
    results_path = RUNS_DIR / args.out if args.out else RESULTS_PATH
    stage_ks = {**STAGE_KS, "reranked": tuple(sorted({1, 3, 5, args.top_k}))}
    settings = {
        "chunking": config.INDEX_VARIANT or "base",
        **{
            k: getattr(args, k)
            for k in ("top_k", "pool", "candidates", "tokenizer", "raw")
        },
    }

    chunks_json = len(json.loads(config.CHUNKS_PATH.read_text(encoding="utf-8")))
    chroma = get_vectorstore()._collection.count()
    if chroma != chunks_json:
        sys.exit(
            f"index mismatch: Chroma {chroma} vs chunks.json {chunks_json}; re-ingest first"
        )

    reranker = (
        CrossEncoderReranker(top_k=args.top_k) if args.top_k != config.TOP_K else None
    )
    keyword = (
        None
        if args.tokenizer == "split"
        else BM25Retriever(tokenizer=TOKENIZERS[args.tokenizer])
    )
    cache = load_rewrites()
    ids = store.run_ids()
    rows = []
    for n, item in enumerate(items, 1):
        query = item["question"] if args.raw else get_rewrite(item["question"], cache)
        with track() as timings:
            stages = retrieve_context(
                query,
                args.top_k,
                reranker,
                pool=args.pool,
                candidates=args.candidates,
                keyword=keyword,
            )
        stages["fused_top5"] = stages["fused"][:5]
        metrics = {
            stage: score(item, stages[stage], ks) for stage, ks in stage_ks.items()
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
                **ids,
                "settings": settings,
                "context_chars": sum(len(c["text"]) for c in stages["reranked"]),
                "rerank_ms": round(
                    sum(t["ms"] for t in timings if t["stage"] == "rerank"), 1
                ),
                "metrics": metrics,
            }
        )
        print(
            f"[{n}/{len(items)}] {item['id']} fused.recall@10={metrics['fused']['recall@10']:.2f} "
            f"reranked.recall@5={metrics['reranked']['recall@5']:.2f} mrr={metrics['reranked']['mrr']:.2f}"
        )
    results_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    print(f"\n{results_path.name}: {ids} prompt {config.PROMPT_VERSION} {settings}")
    chars = sorted(r["context_chars"] for r in rows)
    ms = sorted(r["rerank_ms"] for r in rows)
    print(
        f"context chars mean {sum(chars) / len(chars):.0f}; rerank ms "
        f"p50 {ms[len(ms) // 2]:.0f} p95 {ms[int(len(ms) * 0.95)]:.0f}"
    )
    report_all(rows)
    print("\nSLICES")
    for category in sorted({r["category"] for r in rows}):
        report_slice(category, [r for r in rows if r["category"] == category])
    for origin in ("manual", "synthetic", "upstream"):
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
    assert word_tokens("Aventro's A-350, (SUV).") == [  # nosec B101
        "aventro",
        "s",
        "a",
        "350",
        "suv",
    ]
    assert word_tokens_s("tyres glass bus is") == ["tyre", "glass", "bus", "is"]  # nosec B101


if __name__ == "__main__":
    _selfcheck()
    main()
