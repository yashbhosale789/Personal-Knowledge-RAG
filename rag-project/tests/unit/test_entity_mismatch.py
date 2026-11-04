import pytest

from src.llm.semantic_cache import entity_mismatch


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        # Same question: case, punctuation and filler words do not matter.
        ("tyre pressure", "tyre pressure", False),
        ("Where is the spare tyre in a Sedan?", "where is spare tyre in sedan", False),
        (
            "What's the ZX Bank car loan rate?",
            "what s the zx bank car loan rate",
            False,
        ),
        # c1: vehicle types (the old hard-coded guard).
        (
            "Where is the spare tyre in a Sedan?",
            "Where is the spare tyre in an SUV?",
            True,
        ),
        ("SEDAN", "hatchback", True),
        ("sedan or suv?", "sedan", True),
        # c2: entities no fixed word list covered (F-14).
        ("ZX Bank car loan interest rate", "ZX Bank bike loan interest rate", True),
        ("seats on the Airbus A350", "seats on the Airbus A380", True),
        ("Velvera One Pro battery life", "Velvera One Ultra battery life", True),
        ("ZX Bank branches in Delhi", "ZX Bank branches in Mumbai", True),
        ("flights to Mumbai", "flights from Mumbai", True),
        (
            "Can I drive with the ABS light on?",
            "Can I not drive with the ABS light on?",
            True,
        ),
        # Order matters: same words, opposite question.
        (
            "is a car loan cheaper than a bike loan",
            "is a bike loan cheaper than a car loan",
            True,
        ),
        # Accepted cost: a paraphrase is a miss, not a wrong hit.
        ("spare tyre in a sedan", "spare wheel in a sedan", True),
        ("spare tyre in a sedan", "spare tyre location", True),
    ],
)
def test_entity_mismatch(a, b, expected):
    assert entity_mismatch(a, b) is expected
