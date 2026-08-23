CAVEAT_TEXT = "\n\n[Note: parts of this answer couldnot be fully verified against the source material.]"

def score_confidence(sufficiency: dict, citation_check: dict) -> dict:
    # Combines sufficiency + citation verification into one confidence signal.
    # Pure logic, no LLM call — both inputs are already-computed verdicts.

    # Returns:
    #     {"confidence": "high" | "low", "caveat": str | None}

    if citation_check["grounded"]:
        return {"confidence":"high", "caveat": None}

    return {"confidence":"low", "caveat": CAVEAT_TEXT}