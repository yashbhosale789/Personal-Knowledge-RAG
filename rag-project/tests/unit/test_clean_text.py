import pytest

from src.ingestion.loader import clean_text


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        # Extraction artifacts seen in corpus c2 (15.1).
        ("V elvera One Pro", "Velvera One Pro"),
        ("• F ront Camera: 8MP", "• Front Camera: 8MP"),
        (
            "X V ariant (F rom X for All F uel Types)",
            "X Variant (From X for All Fuel Types)",
        ),
        ("Y our account", "Your account"),
        ("call A ventro Motors Support", "call Aventro Motors Support"),
        (
            "A vailable at all A ventro Service Centers",
            "Available at all Aventro Service Centers",
        ),
        ("tra\ufb03c and o\ufb03ce", "traffic and office"),
        ("\uffff Fortis Hospital", "• Fortis Hospital"),
        # Real single letters and acronyms stay.
        ("A car and I am here", "A car and I am here"),
        ("from X variant upwards", "from X variant upwards"),
        ("10 R&D setup", "10 R&D setup"),
        ("3D setup", "3D setup"),
        ("USB-C cable", "USB-C cable"),
        ("ATM at Gate B", "ATM at Gate B"),
        ("Plain text stays 100% unchanged.", "Plain text stays 100% unchanged."),
    ],
)
def test_clean_text(raw, clean):
    assert clean_text(raw) == clean
