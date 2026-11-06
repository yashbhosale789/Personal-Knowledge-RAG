import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SHOW = (
    "import config; from eval import paths; print(config.DATA_DIR.name, config.STORAGE_DIR.name,"
    " config.CHUNKS_PATH.name, paths.GOLDEN_PATH.name, paths.BASELINE_PATH.name)"
)

C1 = "documents chroma chunks.json golden_dataset.json retrieval_baseline_c1.json"


def _config(corpus: str | None, **extra: str) -> subprocess.CompletedProcess:
    # A fresh interpreter: reloading config in-process would leave stale `from config import` copies.
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("RAG_CORPUS", "RAG_TOP_K") and not k.startswith("RAG_CHUNK_")
    }
    if corpus is not None:
        env["RAG_CORPUS"] = corpus
    env.update(extra)
    return subprocess.run(
        [sys.executable, "-c", SHOW],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,  # the c3 case asserts the failure itself
    )


@pytest.mark.parametrize(
    ("corpus", "paths"),
    [
        (None, C1),  # CI, image and prod
        ("c1", C1),
        (
            "c2",
            "corpus_c2 chroma_c2 chunks_c2.json golden_dataset_c2.json retrieval_baseline_c2.json",
        ),
    ],
)
def test_corpus_selects_its_own_documents_index_dataset_and_results(corpus, paths):
    assert _config(corpus).stdout.split() == paths.split()


def test_unknown_corpus_fails_instead_of_writing_into_c1():
    result = _config("c3")
    assert result.returncode != 0 and "RAG_CORPUS must be c1 or c2" in result.stderr


def test_chunking_variant_gets_its_own_index_and_results():
    out = _config("c2", RAG_CHUNK_SIZE="256", RAG_CHUNK_MERGE_PAGES="1").stdout.split()
    assert out[1:3] == ["chroma_c2_s256o64m", "chunks_c2_s256o64m.json"]
    assert out[4] == "retrieval_baseline_c2_s256o64m.json"


def test_chunking_variant_is_refused_on_c1():
    result = _config(None, RAG_CHUNK_SIZE="256")
    assert result.returncode != 0 and "need RAG_CORPUS=c2" in result.stderr


def test_top_k_override_is_refused_on_c1():
    result = _config(None, RAG_TOP_K="3")
    assert result.returncode != 0 and "RAG_TOP_K needs RAG_CORPUS=c2" in result.stderr
