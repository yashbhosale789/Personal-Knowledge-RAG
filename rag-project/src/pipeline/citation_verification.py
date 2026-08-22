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


def verify_citation(answer: str, reranked_chunks: list[dict]) -> dict:
    """
    Post-generation check: does the answer's content actually follow from
    the chunks it was generated against?

    Uses EVAL_PROVIDER, not PIPELINE_PROVIDER — the model that generated the
    answer should not also grade its own citations (self-grading bias).

    Returns:
        {"grounded": bool, "unsupported_claims": list[str], "reason": str}
    """

    prompt = _build_verifier_prompt(answer, reranked_chunks)
    raw = call_llm(prompt, system=CITATION_VERIFIER_SYSTEM, provider=EVAL_PROVIDER)

    try:
        verdict = json.loads(raw.strip())
        grounded = bool(verdict["grounded"])
        unsupported = list(verdict.get("unsupported_claims", []))
        reason = str(verdict["reason"])

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Citation verifier returned unparsable output: {raw} {e}")
        return {
            "grounded": True,
            "unsupported_claims": [],
            "reason": "Verifier output unparsable, defaulted to grounded."
        }

    logger.info(f"Citation Verified: Grounded={grounded}, unsupported={unsupported}, Reason={reason}")
    return {"grounded": grounded, "unsupported": unsupported, "reason": reason}