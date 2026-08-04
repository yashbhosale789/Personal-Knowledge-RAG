import json
import time
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.advanced_rag import run_advanced_rag_pipeline

logging.basicConfig(level=logging.WARNING, format="%(levelname)s — %(message)s")

DATASET_PATH = Path(__file__).parent / "test_dataset.json"
OUTPUT_PATH = Path(__file__).parent / "eval_results.json"
REQUEST_DELAY = 3  # seconds between calls — free tier rate limit


def collect_results(dataset: list[dict]) -> list[dict]:
    results = []

    for i, item in enumerate(dataset):
        qid = item["id"]
        question = item["question"]
        ground_truth = item["ground_truth"]
        difficulty = item["difficulty"]

        print(f"[{i+1}/{len(dataset)}] {qid} ({difficulty}): {question[:70]}...")

        try:
            output = run_advanced_rag_pipeline(question, return_contexts=True)

            record = {
                "id": qid,
                "difficulty": difficulty,
                "question": question,
                "answer": output["answer"],
                "contexts": output["contexts"],  # list[str] of chunk texts
                "ground_truth": ground_truth,
                "rewritten_query": output.get("rewritten_query", ""),
                "chunks_used": output.get("chunks_used", 0),
            }

            results.append(record)
            print(f"    ✓ {output['answer'][:80]}...")

        except Exception as e:
            print(f"    ✗ FAILED: {e}")
            results.append(
                {
                    "id": qid,
                    "difficulty": difficulty,
                    "question": question,
                    "answer": f"ERROR: {e}",
                    "contexts": [],
                    "ground_truth": ground_truth,
                    "rewritten_query": "",
                    "chunks_used": 0,
                }
            )

        if i < len(dataset) - 1:
            time.sleep(REQUEST_DELAY)

    return results


def main():
    print("=" * 60)
    print("Phase 3 — Collecting Pipeline Outputs")
    print("=" * 60)

    if not DATASET_PATH.exists():
        print(f"ERROR: Dataset not found at {DATASET_PATH}")
        sys.exit(1)

    with open(DATASET_PATH) as f:
        dataset = json.load(f)

    print(f"\nLoaded {len(dataset)} questions\n")

    results = collect_results(dataset)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    success = sum(1 for r in results if not r["answer"].startswith("ERROR"))
    print(f"\n{'='*60}")
    print(f"Done. {success}/{len(results)} succeeded.")
    print(f"Results → {OUTPUT_PATH}")
    print(f"Next:     python eval/ragas_eval.py")


if __name__ == "__main__":
    main()
