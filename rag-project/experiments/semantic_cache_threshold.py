import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from src.embedding.embedder import get_embedding_model

model = get_embedding_model()

pairs = [
    (
        "Where is the spare tyre located in an Aventro Sedan?",
        "Where can I find the spare wheel in an Aventro Sedan?",
        "PARAPHRASE",
    ),
    (
        "What steps should I take to safely park before changing a tyre?",
        "What precautions should I take before starting a tyre change?",
        "PARAPHRASE",
    ),
    (
        "Is it safe to drive at highway speeds for a long distance using the spare tyre?",
        "Can I safely drive far on the highway using the spare wheel?",
        "PARAPHRASE",
    ),
    (
        "Where is the spare tyre located in an Aventro Sedan?",
        "Where is the spare tyre located in an Aventro SUV?",
        "CONFUSABLE",
    ),
    (
        "What is the correct way to tighten lug nuts after fitting the spare tyre?",
        "What should I do after fitting the spare tyre before resuming normal driving?",
        "CONFUSABLE",
    ),
]