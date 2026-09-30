import logging

from langchain_core.documents import Document

from config import TOP_K
from src.vectorstore.store import get_vectorstore

logger = logging.getLogger(__name__)


def retrieve(query: str, top_k: int = TOP_K) -> list[Document]:
    """
    Given a query string, return the top_k most semantically similar chunks.

    Internally: embeds the query → cosine similarity search in Chroma → returns Documents.
    The embedding of the query uses the BGE query prefix automatically via our adapter.
    """

    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search(query, k=top_k)

    logger.info(f"Retrieved {len(results)} chunks for query: '{query[:60]}...'")
    return results


"""
Simple by design. In Phase 2 this function grows to include BM25, fusion, and reranking. 
Right now it's pure dense retrieval — embed the query, find nearest vectors.
"""
