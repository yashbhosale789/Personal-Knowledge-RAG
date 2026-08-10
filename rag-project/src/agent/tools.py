import logging
from typing import Any
from src.pipeline.advanced_rag import run_advanced_rag_pipeline as AdvancedRAGPipeline

logger = logging.getLogger(__name__)


def _format_chunks_for_agent(chunks: list[str]) -> str:
    if not chunks:
        return "No relevant information found in the document."

    parts = []
    for i, text in enumerate(chunks, start=1):
        parts.append(f"[CHUNK {i}]\n{text.strip()}")

    return "\n\n".join(parts)


def build_retriever_tool() -> dict[str, Any]:

    def retrieve(query: str) -> str:
        logger.info(f"Tool called — query: '{query}'")
        try:
            result = AdvancedRAGPipeline(query, return_contexts=True)
            chunks = result.get("contexts", [])
            logger.info(f"Retrieved {len(chunks)} chunks")
            return _format_chunks_for_agent(chunks)
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return f"Retrieval error: {str(e)}"

    return {
        "name": "retrieve",
        "description": (
            "Search the Aventro Motors tyre-changing manual for relevant information. "
            "Input must be a concise search query of 5-10 words. "
            "Use this tool whenever the question requires specific facts from the document."
        ),
        "function": retrieve,
    }


def get_all_tools() -> list[dict[str, Any]]:
    return [build_retriever_tool()]
