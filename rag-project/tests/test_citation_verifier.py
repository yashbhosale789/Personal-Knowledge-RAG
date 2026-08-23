import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.citation_verification import verify_citation

# Real chunk text from the actual PDF — jacking point paragraph
real_chunk = {
    "text": (
        "Position the jack under the jacking point nearest to the flat tyre. "
        "Refer to your owner's manual for the exact point."
    ),
    "metadata": {"filename": "_Aventro Motors- How to Change a Tyre.pdf"},
}

# Fabricated answer: invents a specific location the source never states
fabricated_answer = (
    "The jacking point is located under the reinforced frame rail, "
    "approximately 30cm behind the front wheel well[SOURCE 1]"
)

result = verify_citation(fabricated_answer, [real_chunk])
print(result)

assert (
    result["grounded"] is False
), "Verifier should have flagged the fabricated detail as ungrounded"
print("PASS: verifier correctly caught the fabricated claim")
