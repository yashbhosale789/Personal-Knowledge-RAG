import pytest

from src.llm.semantic_cache import entity_mismatch


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (
            "Where is the spare tyre in a Sedan?",
            "Where is the spare tyre in an SUV?",
            True,
        ),
        ("spare tyre in a sedan", "spare wheel in a sedan", False),
        ("spare tyre in a sedan", "spare tyre location", False),
        ("sedan or suv?", "sedan", True),  # differing sets: err on the side of a miss
        ("SEDAN", "hatchback", True),
        ("tyre pressure", "tyre pressure", False),
    ],
)
def test_entity_mismatch(a, b, expected):
    assert entity_mismatch(a, b) is expected
