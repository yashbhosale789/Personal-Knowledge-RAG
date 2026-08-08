import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sentence_transformers import SentenceTransformer
import requests
from config import (
    EVAL_PROVIDER,
    OPENROUTER_EVALUATOR_MODEL,
    OPENROUTER_EVALUATOR_URL,
    OPENROUTER_EVALUATOR_KEY,
    OPENROUTER_REQUEST_DELAY,
    GROQ_EVALUATOR_MODEL,
    GROQ_API_URL,
    GROQ_EVALUATOR_KEY,
    GROQ_REQUEST_DELAY,
    GEMINI_EVALUATOR_MODEL,
    GEMINI_API_URL,
    GEMINI_EVALUATOR_KEY,
    GEMINI_REQUEST_DELAY,
    EMBEDDINGS_MODEL_NAME
)
_embedder = SentenceTransformer(EMBEDDINGS_MODEL_NAME)

RESULTS_PATH = Path(__file__).parent / "eval_results.json"
SCORES_PATH = Path(__file__).parent / "ragas_scores.json"

# Resolve active provider config at startup
_PROVIDERS = {
    "openrouter": (
        OPENROUTER_EVALUATOR_MODEL,
        OPENROUTER_EVALUATOR_URL,
        OPENROUTER_EVALUATOR_KEY,
        OPENROUTER_REQUEST_DELAY,
    ),
    "groq": (
        GROQ_EVALUATOR_MODEL,
        GROQ_API_URL,
        GROQ_EVALUATOR_KEY,
        GROQ_REQUEST_DELAY,
    ),
    "gemini": (
        GEMINI_EVALUATOR_MODEL,
        GEMINI_API_URL,
        GEMINI_EVALUATOR_KEY,
        GEMINI_REQUEST_DELAY,
    ),
}

if EVAL_PROVIDER not in _PROVIDERS:
    raise ValueError(
        f"Unknown EVAL_PROVIDER '{EVAL_PROVIDER}'. Choose: openrouter | groq | gemini"
    )

ACTIVE_MODEL, ACTIVE_URL, ACTIVE_KEY_ENV, ACTIVE_DELAY = _PROVIDERS[EVAL_PROVIDER]


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------


def call_evaluator(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {os.getenv(ACTIVE_KEY_ENV)}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": ACTIVE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 1024,
    }
    response = requests.post(ACTIVE_URL, headers=headers, json=payload, timeout=60)
    data = response.json()

    if "choices" not in data:
        raise RuntimeError(f"Unexpected response from {EVAL_PROVIDER}: {data}")

    return data["choices"][0]["message"]["content"].strip()


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def score_faithfulness(question: str, answer: str, contexts: list[str]) -> float:
    context_block = "\n\n".join(f"[C{i+1}] {c}" for i, c in enumerate(contexts))

    prompt = f"""You are evaluating whether an answer is faithful to the given context.

Context:
{context_block}

Answer: {answer}

Instructions:
1. Break the answer into individual atomic claims.
2. For each claim, judge whether it is supported by the context.
3. Return ONLY a JSON object in this format:
{{"total": <int>, "supported": <int>}}
No explanation. No markdown."""

    raw = call_evaluator(prompt)
    time.sleep(ACTIVE_DELAY)

    try:
        clean = (
            raw.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )
        data = json.loads(clean)
        return round(data["supported"] / data["total"], 4) if data["total"] > 0 else 1.0
    except Exception:
        return 0.0


def score_context_precision(
    question: str, ground_truth: str, contexts: list[str]
) -> float:
    if not contexts:
        return 0.0

    chunks_block = "\n\n".join(f"[C{i+1}] {c}" for i, c in enumerate(contexts))

    prompt = f"""You are evaluating whether retrieved context chunks are relevant.

Question: {question}
Expected answer: {ground_truth}

Retrieved chunks:
{chunks_block}

Instructions:
For each chunk, judge whether it is useful for producing the expected answer.
Return ONLY a JSON object in this format:
{{"total": <int>, "relevant": <int>}}
No explanation. No markdown."""

    raw = call_evaluator(prompt)
    time.sleep(ACTIVE_DELAY)

    try:
        clean = (
            raw.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )
        data = json.loads(clean)
        return round(data["relevant"] / data["total"], 4) if data["total"] > 0 else 0.0
    except Exception:
        return 0.0


def score_context_recall(ground_truth: str, contexts: list[str]) -> float:
    context_block = "\n\n".join(f"[C{i+1}] {c}" for i, c in enumerate(contexts))

    prompt = f"""You are evaluating whether retrieved contexts cover the expected answer.

Expected answer: {ground_truth}

Retrieved contexts:
{context_block}

Instructions:
1. Split the expected answer into individual sentences.
2. For each sentence, judge whether it can be inferred from the retrieved contexts.
3. Return ONLY a JSON object in this format:
{{"total": <int>, "covered": <int>}}
No explanation. No markdown."""

    raw = call_evaluator(prompt)
    time.sleep(ACTIVE_DELAY)

    try:
        clean = (
            raw.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )
        data = json.loads(clean)
        return round(data["covered"] / data["total"], 4) if data["total"] > 0 else 1.0
    except Exception:
        return 0.0


def score_answer_relevancy(question: str, answer: str, n: int = 3) -> float:
    """
    Generates N synthetic questions from the answer, embeds them,
    and computes mean cosine similarity to the original question.
    Score = mean cosine similarity across N synthetic questions.
    """

    # Skip if answer is a refusal — no claims to generate questions from
    if "don't have enough information" in answer.lower():
        return float("nan")  # excluded from aggregate, not penalised

    prompt = f"""Given the following answer, generate {n} different questions that this answer could be responding to.
Return ONLY a JSON array of {n} question strings. No explanation. No markdown.

Answer: {answer}

Example output: ["What color is the sky?", "Why is the sky blue?", "What does the sky look like?"]"""

    raw = call_evaluator(prompt)
    time.sleep(ACTIVE_DELAY)

    try:
        clean = (
            raw.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )
        synthetic_question = json.load(clean)
        if not isinstance(synthetic_question, list) or len(synthetic_question) == 0:
            return 0.0

    except Exception:
        return 0.0

    # Embed original question and all synthetic questions
    all_texts = [question] + synthetic_question
    embeddings = _embedder.encode(all_texts, normalize_embeddings=True)

    original_emb = embeddings[0]
    synthetic_emb = embeddings[1:]

    # Cosine similarity = dot product when embeddings are normalised
    similarities = [float(np.dot(original_emb, syn_emb)) for syn_emb in synthetic_emb]
    return round(float(np.mean(similarities)), 4)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 60)
    print("Phase 3 — RAG Evaluation (LLM-as-Judge)")
    print(f"Provider: {EVAL_PROVIDER} — model: {ACTIVE_MODEL}")
    print("=" * 60)

    if not RESULTS_PATH.exists():
        print(f"ERROR: {RESULTS_PATH} not found. Run run_eval.py first.")
        sys.exit(1)

    with open(RESULTS_PATH) as f:
        records = json.load(f)

    valid = [r for r in records if not r["answer"].startswith("ERROR")]
    print(f"\nEvaluating {len(valid)} records...\n")

    # Resume support
    if SCORES_PATH.exists():
        with open(SCORES_PATH) as f:
            existing = json.load(f)
        already_scored = {r["id"] for r in existing}
        print(f"Resuming — {len(already_scored)} already scored: {already_scored}\n")
    else:
        existing = []
        already_scored = set()

    scored = []
    for i, r in enumerate(valid):
        qid = r["id"]

        if qid in already_scored:
            print(f"[{i+1}/{len(valid)}] {qid} — skipping (already scored)")
            continue

        print(f"[{i+1}/{len(valid)}] {qid} — {r['question'][:55]}...")

        faith = score_faithfulness(r["question"], r["answer"], r["contexts"])
        print(f"  faithfulness:      {faith}")

        prec = score_context_precision(r["question"], r["ground_truth"], r["contexts"])
        print(f"  context_precision: {prec}")

        rec = score_context_recall(r["ground_truth"], r["contexts"])
        print(f"  context_recall:    {rec}")

        ar = score_answer_relevancy(r["question"], r["answer"])
        print(f"  answer_relevancy:  {ar}")

        scored.append(
            {
                **r,
                "faithfulness": faith,
                "context_precision": prec,
                "context_recall": rec,
                "answer_relevancy" : ar
            }
        )

    all_scored = existing + scored

    with open(SCORES_PATH, "w") as f:
        json.dump(all_scored, f, indent=2)

    if not all_scored:
        print("No scores yet.")
        return

    ar_scores = [
        s["answer_relevancy"]
        for s in all_scored
        if not (
            isinstance(s["answer_relevancy"], float) and np.isnan(s["answer_relevancy"])
        )
    ]

    avg_faith = round(sum(s["faithfulness"] for s in all_scored) / len(all_scored), 4)
    avg_prec = round(
        sum(s["context_precision"] for s in all_scored) / len(all_scored), 4
    )
    avg_rec = round(sum(s["context_recall"] for s in all_scored) / len(all_scored), 4)
    avg_ar = round(sum(ar_scores) / len(ar_scores), 4) if ar_scores else float("nan")

    print("\n" + "=" * 60)
    print(f"SCORES SO FAR ({len(all_scored)}/{len(valid)} questions)")
    print("=" * 60)
    print(f"  Faithfulness:      {avg_faith}")
    print(f"  Context Precision: {avg_prec}")
    print(f"  Context Recall:    {avg_rec}")
    print(f"  Answer Relevancy:  {avg_ar} (excludes refusal answers)")

    print("\nPer-question:")
    print("-" * 60)
    for s in all_scored:
        print(
            f"  {s['id']} ({s['difficulty']:<6}) "
            f"F={s['faithfulness']:.2f}  "
            f"P={s['context_precision']:.2f}  "
            f"R={s['context_recall']:.2f}  "
            f"— {s['question'][:45]}"
        )

    print(f"\nFull results saved to: {SCORES_PATH}")


if __name__ == "__main__":
    main()