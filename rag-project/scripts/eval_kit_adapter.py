"""Production RAG as a rag-eval-kit adapter (Phase 16.4).

Retrieval only, $0: queries come from the stored rewrite cache; a cache miss stops the run
instead of calling the LLM. Run from rag-project/ with the kit installed in this venv:
    rag-eval-kit retrieval --adapter scripts.eval_kit_adapter:Production \
        --dataset eval/data/golden_dataset.json --out <file>
"""

import json

import config
from eval.harness.retrieval_eval import chunk_source, load_rewrites
from eval.harness.store import content_id, fingerprint
from src.pipeline.advanced_rag import retrieve_context
from src.vectorstore.store import get_vectorstore


class Production:
    def __init__(self) -> None:
        chunks_json = len(json.loads(config.CHUNKS_PATH.read_text(encoding="utf-8")))
        chroma = get_vectorstore()._collection.count()
        if chroma != chunks_json:
            raise SystemExit(
                f"index mismatch: Chroma {chroma} vs chunks.json {chunks_json}; re-ingest first"
            )
        self.rewrites = load_rewrites()["rewrites"]
        self.version = fingerprint()
        self.corpus_id = content_id(config.CHUNKS_PATH)

    def retrieve(self, question: str) -> list[dict]:
        if question not in self.rewrites:
            raise RuntimeError(
                f"rewrite cache miss: {question!r}; filling it costs LLM calls, ask the owner"
            )
        ranked = retrieve_context(self.rewrites[question], config.TOP_K, None)["reranked"]
        return [{"text": c["text"], "source": chunk_source(c)} for c in ranked]
