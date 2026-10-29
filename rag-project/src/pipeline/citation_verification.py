import json
import logging
import re

import requests

from config import CITATION_VERIFIER_MODEL, CITATION_VERIFIER_SYSTEM, EVAL_PROVIDER
from src.llm.client import call_llm
from src.pipeline.json_reply import parse_json_reply

logger = logging.getLogger(__name__)

_CITATION_PATTERN = re.compile(r"[\[【]\s*SOURCE\s*\d+\s*[\]】]", re.IGNORECASE)


def _has_citation(answer: str) -> bool:
    # Tier 1: cheap check, no LLM call. True if at least one [SOURCE N] marker is present.
    return bool(_CITATION_PATTERN.search(answer))


def _build_verifier_prompt(answer: str, cited_chunks: list[dict]) -> str:
    sources = "\n\n".join(
        f"[SOURCE {i}]\n {c['text']}" for i, c in enumerate(cited_chunks, 1)
    )
    return f"ANSWER:\n{answer}\n\nCITED SOURCES:\n{sources}"


def verify_citation(answer: str, reranked_chunks: list[dict]) -> dict:
    """
    Post-generation check: does the answer's content actually follow from
    the chunks it was generated against?

    Uses EVAL_PROVIDER with CITATION_VERIFIER_MODEL when it is set. Outside Groq,
    CITATION_VERIFIER_MODEL is None and the verifier uses EVAL_PROVIDER's pipeline
    model, which matches the generator's model when both use the same provider.

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
    try:
        raw = call_llm(
            prompt,
            system=CITATION_VERIFIER_SYSTEM,
            provider=EVAL_PROVIDER,
            stage="citation_verify",
            model=CITATION_VERIFIER_MODEL,
        )
    except (requests.exceptions.RequestException, ValueError, KeyError) as e:
        # Degrade, don't fail: an EVAL_PROVIDER outage must not turn every answer into a 502.
        logger.warning(f"Citation verifier unavailable ({EVAL_PROVIDER}): {e}")
        return {
            "grounded": False,
            "unsupported_claims": [],
            "reason": "Citation verifier unavailable.",
            "tier": "verifier_error",
        }

    try:
        verdict = parse_json_reply(raw)
        grounded = bool(verdict["grounded"])
        unsupported = list(verdict.get("unsupported_claims", []))
        reason = str(verdict["reason"])

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Citation verifier returned unparsable output: {raw} {e}")
        return {
            "grounded": False,
            "unsupported_claims": [],
            "reason": "Citation verifier returned unparsable output.",
            "tier": "llm_judge",
        }

    logger.info(
        f"Citation Verified: grounded={grounded}, unsupported_claims={unsupported}, reason={reason}"
    )
    return {
        "grounded": grounded,
        "unsupported_claims": unsupported,
        "reason": reason,
        "tier": "llm_judge",
    }
