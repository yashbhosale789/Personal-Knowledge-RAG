import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SHOW = "import config; print(config.DATA_DIR.name, config.STORAGE_DIR.name, config.CHUNKS_PATH.name)"


def _config(corpus: str | None) -> subprocess.CompletedProcess:
    # A fresh interpreter: reloading config in-process would leave stale `from config import` copies.
    env = {k: v for k, v in os.environ.items() if k != "RAG_CORPUS"}
    if corpus is not None:
        env["RAG_CORPUS"] = corpus
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
        (None, "documents chroma chunks.json"),  # CI, image and prod
        ("c1", "documents chroma chunks.json"),
        ("c2", "corpus_c2 chroma_c2 chunks_c2.json"),
    ],
)
def test_corpus_selects_its_own_documents_index_and_export(corpus, paths):
    assert _config(corpus).stdout.split() == paths.split()


def test_unknown_corpus_fails_instead_of_writing_into_c1():
    result = _config("c3")
    assert result.returncode != 0 and "RAG_CORPUS must be c1 or c2" in result.stderr
