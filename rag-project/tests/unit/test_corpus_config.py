import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHOW = (
    "import config; from eval import paths; print(config.DATA_DIR.name, config.STORAGE_DIR.name,"
    " config.CHUNKS_PATH.name, paths.GOLDEN_PATH.name, paths.BASELINE_PATH.name,"
    " config.CHUNK_SIZE, config.CHUNK_OVERLAP, config.TOP_K)"
)


def _config(**extra: str) -> list[str]:
    # A fresh interpreter: reloading config in-process would leave stale `from config import` copies.
    env = {
        k: v
        for k, v in os.environ.items()
        if k != "RAG_TOP_K" and not k.startswith("RAG_CHUNK_")
    }
    env.update(extra)
    result = subprocess.run(
        [sys.executable, "-c", SHOW],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.split()


def test_one_corpus_with_the_15_2_chunking_by_default():
    # CI, the image and prod: data/documents, storage/chroma, 1024/64, TOP_K 3.
    assert _config() == [
        "documents",
        "chroma",
        "chunks.json",
        "golden_dataset.json",
        "retrieval_baseline_current.json",
        "1024",
        "64",
        "3",
    ]


def test_chunking_experiment_gets_its_own_index_and_results():
    out = _config(RAG_CHUNK_SIZE="256", RAG_CHUNK_MERGE_PAGES="1")
    assert out[1:3] == ["chroma_s256o64m", "chunks_s256o64m.json"]
    assert out[4] == "retrieval_baseline_current_s256o64m.json"
