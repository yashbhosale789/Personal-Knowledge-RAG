"""Integration harness: temp Chroma + fake embedder + real BM25 + real ingest code.

All tests talk to the index through `Stack` (ingest, query, delete) so they survive
a storage change in Phase 15.0 — only this file needs to learn the new storage.
"""

import importlib.util
import json
from pathlib import Path

import pytest
from langchain_core.documents import Document

import config
from tests.conftest import FakeReranker

SCRIPT = Path(config.BASE_DIR) / "scripts" / "ingest.py"


def make_text(token: str, paragraphs: int = 3) -> str:
    """~paragraphs chunk-sized paragraphs, each carrying `token` so BM25/dense can find it."""
    return "\n\n".join(
        f"{token} section {i}. " + ("Tighten the lug nuts in a star pattern. " * 12)
        for i in range(paragraphs)
    )


class Stack:
    def __init__(self, monkeypatch, tmp_path):
        self.mp = monkeypatch
        self.docs_dir = tmp_path / "documents"
        self.docs_dir.mkdir()
        self.chunks_path = tmp_path / "storage" / "chunks.json"
        self._texts: dict[str, str] = {}
        self.cache_clears = 0

        from api.routers import ingest as ingest_router
        from src.pipeline import advanced_rag
        from src.retrieval import bm25_retriever
        from src.vectorstore import store

        monkeypatch.setattr(store, "STORAGE_DIR", tmp_path / "chroma")
        monkeypatch.setattr(config, "DATA_DIR", self.docs_dir)
        monkeypatch.setattr(config, "CHUNKS_PATH", self.chunks_path)
        monkeypatch.setattr(
            advanced_rag,
            "BM25Retriever",
            lambda: bm25_retriever.BM25Retriever(self.chunks_path),
        )
        monkeypatch.setattr(advanced_rag, "_bm25", None)
        monkeypatch.setattr(advanced_rag, "_reranker", FakeReranker())
        monkeypatch.setattr(ingest_router, "clear_cache", self._count_clear)
        monkeypatch.setattr("src.ingestion.loader.load_documents", self._fake_load)

        self.store = store
        self.advanced_rag = advanced_rag
        self.ingest_router = ingest_router

    # -- plumbing ------------------------------------------------------------

    def _count_clear(self) -> int:
        self.cache_clears += 1
        return 0

    def _fake_load(self, path: Path) -> list[Document]:
        text = self._texts[Path(path).name]
        return [
            Document(
                page_content=text, metadata={"source": str(path), "filename": str(path)}
            )
        ]

    def _write(self, name: str, text: str) -> Path:
        self._texts[name] = text
        path = self.docs_dir / name
        path.write_bytes(b"%PDF-1.4 placeholder")
        return path

    def _script(self):
        spec = importlib.util.spec_from_file_location("ingest_script", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.DATA_DIR = self.docs_dir
        module.CHUNKS_PATH = self.chunks_path
        module.load_directory = self._load_directory
        return module

    def _load_directory(self, _directory) -> list[Document]:
        return [
            doc
            for name in sorted(self._texts)
            for doc in self._fake_load(self.docs_dir / name)
        ]

    # -- the three operations the tests use ---------------------------------

    def baked_ingest(self, **docs: str) -> None:
        """What `scripts/ingest.py` does at image-build time. Adds/updates the given docs."""
        for name, text in docs.items():
            self._write(f"{name}.pdf", text)
        self._script().main()
        self.restart_bm25()

    def api_ingest(self, name: str, text: str) -> None:
        path = self._write(f"{name}.pdf", text)
        self.ingest_router._run_ingest(str(path), False)

    def api_delete(self, name: str) -> None:
        self.ingest_router._run_delete(str(self.docs_dir / f"{name}.pdf"))

    def query(self, text: str) -> dict[str, list[str]]:
        stages = self.advanced_rag.retrieve_context(text)
        return {stage: [c["text"] for c in chunks] for stage, chunks in stages.items()}

    # -- inspection -----------------------------------------------------------

    def restart_bm25(self) -> None:
        """Simulates an app restart: BM25 is rebuilt from chunks.json."""
        self.mp.setattr(self.advanced_rag, "_bm25", None)

    def dense_count(self) -> int:
        return self.store.get_vectorstore()._collection.count()

    def chunks_json(self) -> list[dict]:
        return json.loads(self.chunks_path.read_text(encoding="utf-8"))


@pytest.fixture
def stack(monkeypatch, tmp_path, fake_embeddings):
    return Stack(monkeypatch, tmp_path)
