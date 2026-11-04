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


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


from src.llm.semantic_cache import entity_mismatch

for query_a, query_b, label in pairs:
    embedding_a = model.encode(query_a)
    embedding_b = model.encode(query_b)
    similarity = cosine_similarity(embedding_a, embedding_b)
    blocked = entity_mismatch(query_a, query_b)
    would_cache = similarity >= 0.90 and not blocked
    print(
        f'[{label}] sim={similarity:.4f}  blocked={blocked}  would_cache={would_cache}  |  "{query_a}"  vs  "{query_b}"'
    )
