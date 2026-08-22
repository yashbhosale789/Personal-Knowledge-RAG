import json
import logging

from src.llm.client import call_llm
from config import CITATION_VERIFIER_SYSTEM, EVAL_PROVIDER

logger = logging.getLogger(__name__)


def _build_verifier_prompt(answer: str, cited_chunks: list[dict]) -> str:
    sources = "\n\n".join(
        f"[SOURCE {i}]\n {c['text']}" for i, c in enumerate(cited_chunks, 1)
    )
    return f"ANSWEER:\n{answer}\n\nCITED SOURCES:\n{sources}"


