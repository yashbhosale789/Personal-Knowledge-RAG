import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

RESULTS_PATH = Path(__file__).parent / "eval_results.json"
SCORES_PATH = Path(__file__).parent / "ragas_scores.json"

EVALUATOR_MODEL = "nvidia/nemotron-3-nano-30b-a3b:free"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
REQUEST_DELAY = 8  # seconds between LLM calls


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------


def call_evaluator(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/personal-kb-rag",
    }
    payload = {
        "model": EVALUATOR_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 1024,
    }
    response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    data = response.json()

    if "choices" not in data:
        raise RuntimeError(f"Unexpected response: {data}")

    return data["choices"][0]["message"]["content"].strip()


# ---------------------------------------------------------------------------
# Metric: Faithfulness
# Decompose answer into claims, verify each against contexts.
# Score = supported_claims / total_claims
# ---------------------------------------------------------------------------


def score_faithfulness(question: str, answer: str, contexts: list[str]) -> float:
    context_block = "\n\n".join(f"[C{i+1}] {c}" for i, c in enumerate(contexts))

    # Step 1: extract atomic claims from answer
    claim_prompt = f"""Break the following answer into individual atomic claims.
Each claim must be a single verifiable statement.
Return ONLY a JSON array of strings. No explanation. No markdown.

Answer: {answer}

Example output: ["The sky is blue.", "Water boils at 100 degrees."]"""

    raw = call_evaluator(claim_prompt)
    time.sleep(REQUEST_DELAY)

    try:
        # Strip markdown fences if model adds them
        clean = (
            raw.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )
        claims = json.loads(clean)
    except Exception:
        # If parsing fails, treat as single claim
        claims = [answer]

    if not claims:
        return 1.0

    # Step 2: verify each claim against context
    supported = 0
    for claim in claims:
        verify_prompt = f"""Given the following context, is the claim supported?
Answer ONLY with YES or NO.

Context:
{context_block}

Claim: {claim}"""

        verdict = call_evaluator(verify_prompt).strip().upper()
        time.sleep(REQUEST_DELAY)
        if verdict.startswith("YES"):
            supported += 1

    return round(supported / len(claims), 4)


# ---------------------------------------------------------------------------
# Metric: Context Precision
# For each retrieved chunk, is it relevant to the ground truth?
# Score = relevant_chunks / total_chunks
# ---------------------------------------------------------------------------


def score_context_precision(
    question: str, ground_truth: str, contexts: list[str]
) -> float:
    if not contexts:
        return 0.0

    relevant = 0
    for i, ctx in enumerate(contexts):
        prompt = f"""Given the question and the expected answer, is the following context chunk useful for producing that answer?
Answer ONLY with YES or NO.

Question: {question}
Expected answer: {ground_truth}
Context chunk: {ctx}"""

        verdict = call_evaluator(prompt).strip().upper()
        time.sleep(REQUEST_DELAY)
        if verdict.startswith("YES"):
            relevant += 1

    return round(relevant / len(contexts), 4)


# ---------------------------------------------------------------------------
# Metric: Context Recall
# For each sentence in ground truth, is it covered by the retrieved contexts?
# Score = covered_sentences / total_sentences
# ---------------------------------------------------------------------------


def score_context_recall(ground_truth: str, contexts: list[str]) -> float:
    context_block = "\n\n".join(f"[C{i+1}] {c}" for i, c in enumerate(contexts))

    # Split ground truth into sentences
    sentences = [
        s.strip() for s in ground_truth.replace("?", ".").split(".") if s.strip()
    ]

    if not sentences:
        return 1.0

    covered = 0
    for sentence in sentences:
        prompt = f"""Can the following statement be inferred or found in the context below?
Answer ONLY with YES or NO.

Statement: {sentence}

Context:
{context_block}"""

        verdict = call_evaluator(prompt).strip().upper()
        time.sleep(REQUEST_DELAY)
        if verdict.startswith("YES"):
            covered += 1

    return round(covered / len(sentences), 4)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 60)
    print("Phase 3 — RAG Evaluation (LLM-as-Judge)")
    print(f"Evaluator model: {EVALUATOR_MODEL}")
    print("=" * 60)

    if not RESULTS_PATH.exists():
        print(f"ERROR: {RESULTS_PATH} not found. Run run_eval.py first.")
        sys.exit(1)

    with open(RESULTS_PATH) as f:
        records = json.load(f)

    valid = [r for r in records if not r["answer"].startswith("ERROR")]
    print(f"\nEvaluating {len(valid)} records...\n")

    scored = []
    for i, r in enumerate(valid):
        qid = r["id"]
        print(f"[{i+1}/{len(valid)}] {qid} — {r['question'][:55]}...")

        faith = score_faithfulness(r["question"], r["answer"], r["contexts"])
        print(f"  faithfulness:      {faith}")

        prec = score_context_precision(r["question"], r["ground_truth"], r["contexts"])
        print(f"  context_precision: {prec}")

        rec = score_context_recall(r["ground_truth"], r["contexts"])
        print(f"  context_recall:    {rec}")

        scored.append(
            {
                **r,
                "faithfulness": faith,
                "context_precision": prec,
                "context_recall": rec,
            }
        )

    # Aggregate
    avg_faith = round(sum(s["faithfulness"] for s in scored) / len(scored), 4)
    avg_prec = round(sum(s["context_precision"] for s in scored) / len(scored), 4)
    avg_rec = round(sum(s["context_recall"] for s in scored) / len(scored), 4)

    print("\n" + "=" * 60)
    print("FINAL SCORES")
    print("=" * 60)
    print(f"  Faithfulness:      {avg_faith}")
    print(f"  Context Precision: {avg_prec}")
    print(f"  Context Recall:    {avg_rec}")

    print("\nPer-question:")
    print("-" * 60)
    for s in scored:
        print(
            f"  {s['id']} ({s['difficulty']:<6}) "
            f"F={s['faithfulness']:.2f}  "
            f"P={s['context_precision']:.2f}  "
            f"R={s['context_recall']:.2f}  "
            f"— {s['question'][:45]}"
        )

    with open(SCORES_PATH, "w") as f:
        json.dump(scored, f, indent=2)

    print(f"\nFull results saved to: {SCORES_PATH}")


if __name__ == "__main__":
    main()
