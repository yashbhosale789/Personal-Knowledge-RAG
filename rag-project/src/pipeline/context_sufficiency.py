import json
import logging
from src.llm.client import call_llm
from config import SUFFICIENCY_CE_FLOOR, SUFFICIENCY_JUDGE_SYSTEM, PIPELINE_PROVIDER

logger = logging.getLogger(__name__)


def _build_judge_prompt(query: str, chunks: list[dict]) -> str:
    context = "\n\n".join(c["text"] for c in chunks)
    return f"Question:\n{query}\n\nContext:\n{context}"


def check_sufficiency(query: str, reranked_chunks: list[dict]) -> dict:
    if not reranked_chunks:
        return {"sufficient": False, "reason": "No chunks retrieved.", "tier": "empty"}

    top_score = reranked_chunks[0]["ce_score"]

    # Tier 1: Cheap floor check, no llm call
    if top_score < SUFFICIENCY_CE_FLOOR:
        logger.info(f"Sufficiency: tier1 reject (ce_score={top_score:.4f} < floor)")
        return {
            "sufficient": False,
            "reason": f"Top reranker score ({top_score:.2f}) below relevance floor.",
            "tier": "score_floor",
        }

    # Tier 2: LLM judge on the ambigous middle
    prompt = _build_judge_prompt(query, reranked_chunks)
    raw = call_llm(prompt, system=SUFFICIENCY_JUDGE_SYSTEM)

    try:
        verdict = json.loads(raw.strip())
        sufficient = bool(verdict["sufficient"])
        reason = str(verdict["reason"])

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Sufficiency judge returned unparsable output : {raw} ({e})")
        # Fail open: don't block answering just because the judge malformed its output.
        # ponytail: naive fail-open on parse error. Upgrade: retry once, then fail closed if still bad.
        return {
            "sufficient": True,
            "reason": "Judge output unparsable, defaulted to sufficient.",
            "tier": "llm_judge",
        }

    logger.info(f"Sufficiency: tier2 verdict = {sufficient} reason = {reason}")
    return {"sufficient": sufficient, "reason": reason, "tier": "llm_judge"}