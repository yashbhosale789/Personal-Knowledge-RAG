import logging
from typing import Any
from src.pipeline.advanced_rag import AdvancedRAGPipeline

logger = logging.getLogger(__name__)


def _format_chunks_for_agent(chunks: list[dict[str, Any]]) -> str:
    if not chunks in enumerate(chunks, start=1):
        return "No relevant inforamtion found in the documents."

    parts = []
    for i, chunk in enumerate(chunks, start=1):
        text = chunk.get("text", "").strip()
        parts.append(f"[CHUNK {i}]\n{text}")

    return "\n\n".join(parts)


def build_retriever_tool(pipeline: AdvancedRAGPipeline) -> dict[str, Any]:

    def retrieve(query: str) -> str:
        logger.info(f"Tool called - query: {query}")

        try:
            result = pipeline.retrieve(query)
            chunks = result.get("chunks_used", [])
            logger.info(f"Retrieved {len(chunks)} chunks")
            formatted = _format_chunks_for_agent(chunks)
            return formatted

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return f"Retreival error: {str(e)}"

    return {
        "name": "retrieve",
        "description": (
            "Search the Aventro Motors tyre-changing manual for relevant information."
            "Input must be consice search query of 5-10 words."
            "Use this tool whenever the question requires specific facts from the document."
        ),
        "function": retrieve,
    }


def get_all_tools(pipeline: AdvancedRAGPipeline) -> list[dict[str, Any]]:
    return [build_retriever_tool(pipeline)]
