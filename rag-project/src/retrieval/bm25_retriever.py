import logging
from collections.abc import Callable

from rank_bm25 import BM25Okapi

from config import TOP_K

logger = logging.getLogger(__name__)


def tokenize(text: str) -> list[str]:
    return text.lower().split()


class BM25Retriever:
    """
    Keyword retriever backed by BM25Okapi.

    Built from the chunks stored in Chroma (the single source of truth, Phase 15.0),
    so it never drifts from dense retrieval. Rebuilt after every ingest or delete.
    Tokenisation is whitespace split — sufficient for English prose.
    For production, swap in a proper tokenizer (spaCy, NLTK punkt).
    """

    def __init__(
        self,
        chunks: list[dict] | None = None,
        tokenizer: Callable[[str], list[str]] = tokenize,
    ):
        if chunks is None:
            from src.vectorstore.store import all_chunks

            chunks = all_chunks()
        self._chunks = chunks
        self._corpus = [c["text"] for c in self._chunks]
        self._tokenize = tokenizer
        self._tokenized = [tokenizer(doc) for doc in self._corpus]
        # BM25Okapi divides by the corpus size, so an empty index has no BM25 object.
        self._index = BM25Okapi(self._tokenized) if self._tokenized else None
        if self._index is None:
            logger.warning("BM25 index is empty: no chunks in the vector store")
        else:
            logger.info(f"BM25 index built over {len(self._chunks)} chunks")

    def retrieve(self, query: str, top_k: int = TOP_K) -> list[dict]:
        """
        Returns top_k chunks as dicts: {text, metadata, score, rank}.
        Score is a raw BM25 float — only meaningful relative to other scores
        from this same query. Do not compare across queries.
        """
        if self._index is None:
            return []

        tokens = self._tokenize(query)
        scores = self._index.get_scores(tokens)

        ranked_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )

        results = []

        for rank, idx in enumerate(ranked_indices[:top_k]):
            results.append(
                {
                    "text": self._chunks[idx]["text"],
                    "metadata": self._chunks[idx]["metadata"],
                    "score": float(scores[idx]),
                    "rank": rank,
                }
            )

        return results
