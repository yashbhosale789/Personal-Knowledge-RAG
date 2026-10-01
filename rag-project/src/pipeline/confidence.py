CAVEAT_TEXT = "\n\n[Note: parts of this answer could not be fully verified against the source material.]"


def score_confidence(citation_check: dict) -> dict:
    """
    Confidence is driven entirely by citation groundedness. Sufficiency already
    gated generation upstream (insufficient context aborts before this point
    via 'abstain'), so it carries no further usable signal here — empirically
    confirmed against eval data: ce_score does not correlate with answer
    quality/correctness (e.g. Q02, one of the cleanest correct answers in the
    eval set, had the lowest ce_score of any 'sufficient' case).

    Returns:
        {"confidence": "high" | "low", "caveat": str | None}
    """

    if citation_check["grounded"]:
        return {"confidence": "high", "caveat": None}

    return {"confidence": "low", "caveat": CAVEAT_TEXT}
