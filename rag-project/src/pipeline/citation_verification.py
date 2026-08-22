import json
import logging
import re

from src.llm.client import call_llm
from config import CITATION_VERIFIER_SYSTEM, EVAL_PROVIDER

logger = logging.getLogger(__name__)

_CITATION_PATTERN = re.compile(r"[\[【]SOURCE\s*\d+[\]】]")


def _has_citation(answer: str) -> bool:
    # Tier 1: cheap check, no LLM call. True if at least one [SOURCE N] marker is present.
    return bool(_CITATION_PATTERN.search(answer))


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

    if not _has_citation(answer):
        logger.info(
            "Citation verification: tier 1 reject (no [SOURCE N] markers found)"
        )
        return {
            "grounded": False,
            "unsupported_claims": [],
            "reason": "Answer contains no citation markers.",
            "tier": "no_citations",
        }

    # Tier 2: LLM judge — answer has citations, check if they're actually supported
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
            "grounded": False,
            "unsupported_claims": [],
            "reason": "Answer contains no citation markers.",
            "tier": "llm_judge"
        }

    logger.info(
        f"Citation Verified: Grounded={grounded}, unsupported={unsupported}, Reason={reason}"
    )
    return {"grounded": grounded, "unsupported": unsupported, "reason": reason, "tier": "llm_judge"}
