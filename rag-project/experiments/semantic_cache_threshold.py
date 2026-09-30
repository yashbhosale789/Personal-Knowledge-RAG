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


from config import ENTITY_GROUPS


def entity_mismatch(query_a: str, query_b: str) -> bool:
    query_a_lower = query_a.lower()
    query_b_lower = query_b.lower()

    for group in ENTITY_GROUPS:
        terms_in_a = {term for term in group if term in query_a_lower}
        terms_in_b = {term for term in group if term in query_b_lower}

        if terms_in_a and terms_in_b and terms_in_a != terms_in_b:
            return True

    return False


for query_a, query_b, label in pairs:
    embedding_a = model.encode(query_a)
    embedding_b = model.encode(query_b)
    similarity = cosine_similarity(embedding_a, embedding_b)
    blocked = entity_mismatch(query_a, query_b)
    would_cache = similarity >= 0.90 and not blocked
    print(
        f'[{label}] sim={similarity:.4f}  blocked={blocked}  would_cache={would_cache}  |  "{query_a}"  vs  "{query_b}"'
    )
