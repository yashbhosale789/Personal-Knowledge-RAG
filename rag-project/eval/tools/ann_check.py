"""Phase 15.2 ANN check: Chroma's HNSW top-k vs exact cosine top-k over the stored vectors.

RAG_CORPUS=c2 python -m eval.tools.ann_check   (dev split, cached rewrites, no LLM calls)
"""

import json

import numpy as np

import config
from eval.harness import store
from eval.harness.retrieval_eval import load_rewrites, score
from eval.paths import GOLDEN_PATH
from src.embedding.embedder import embed_query
from src.vectorstore.store import get_vectorstore


def exact_top(matrix: np.ndarray, query: np.ndarray, k: int) -> list[int]:
    sims = matrix @ query / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(query))
    return [int(i) for i in np.argsort(-sims, kind="stable")[:k]]


def main() -> None:
    items = [
        i
        for i in json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
        if i["expected_outcome"] == "answer" and i["split"] == "dev"
    ]
    rewrites = load_rewrites()["rewrites"]
    col = get_vectorstore()._collection
    got = col.get(include=["embeddings", "documents", "metadatas"])
    ids, matrix = got["ids"], np.asarray(got["embeddings"], dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1)
    print(
        f"{store.run_ids()} prompt {config.PROMPT_VERSION}; {len(ids)} vectors, "
        f"norm min {norms.min():.4f} max {norms.max():.4f}; n={len(items)} dev"
    )

    chunk = {
        i: {"text": d, "metadata": m}
        for i, d, m in zip(ids, got["documents"], got["metadatas"])
    }
    for k in (config.TOP_K, config.TOP_K * 4):
        overlap, same, recall_ann, recall_exact = [], 0, [], []
        for item in items:
            q = embed_query(rewrites[item["question"]])
            ann = col.query(query_embeddings=[q], n_results=k)["ids"][0]
            exact = [ids[i] for i in exact_top(matrix, np.asarray(q), k)]
            overlap.append(len(set(ann) & set(exact)) / k)
            same += set(ann) == set(exact)
            recall_ann.append(score(item, [chunk[i] for i in ann], (k,))[f"recall@{k}"])
            recall_exact.append(
                score(item, [chunk[i] for i in exact], (k,))[f"recall@{k}"]
            )
        n = len(items)
        diffs = [a - e for a, e in zip(recall_ann, recall_exact)]
        print(
            f"top-{k}: mean overlap {sum(overlap) / n:.4f}, identical sets {same}/{n}, "
            f"recall@{k} ANN {sum(recall_ann) / n:.3f} exact {sum(recall_exact) / n:.3f}, "
            f"questions differing {sum(d != 0 for d in diffs)}"
        )


def _selfcheck() -> None:
    m = np.array([[1.0, 0.0], [0.6, 0.8], [0.0, 1.0]])
    assert exact_top(m, np.array([0.0, 2.0]), 2) == [2, 1]  # nosec B101


if __name__ == "__main__":
    _selfcheck()
    main()
