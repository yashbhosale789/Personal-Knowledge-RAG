import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from ragas import evaluate
from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
from ragas.metrics import (
    Faithfulness,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
)
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI

RESULTS_PATH = Path(__file__).parent / "eval_results.json"
EVALUATOR_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
EVALUATOR_BASE_URL = "https://openrouter.ai/api/v1"

def build_evaluator_llm() -> LangchainLLMWrapper :
    llm = ChatOpenAI(
        model = EVALUATOR_MODEL,
        openai_api_key = os.getenv("OPENROUTER_API_KEY"),
        openai_api_base = EVALUATOR_BASE_URL,
        temperature = 0.0,
        max_tokens = 1024,
        default_headers={
            "HTTP-Referer": "https://github.com/personal-kb-rag"
        }
    )
    return LangchainLLMWrapper(llm)


def load_dataset(path: Path) -> EvaluationDataset:
    with open(path) as f:
        records = json.load(f)

    samples = []
    for r in records:
        if r["answer"].startswith("ERROR"):
            print(f"Skipping {r['id']} - pipeline error")
            continue

        sample = SingleTurnSample(
            user_input=r["question"],
            response=r["answer"],
            retrieved_contexts=r["contexts"],
            reference=r["ground_truth"]
        )
        samples.append(sample)

    print(f"Loaded {len(samples)} valid samples.")
    return EvaluationDataset(samples=samples)


def print_results(results):
    df = results.to_pandas()

    metri_cols = [
        c for c in df.columns
        if c not in ("user_inputs", "response", "retreived_contexts", "reference")
    ]

    print("\n" + "="  * 60)
    print("RAGAS SCORES - AGGREGATE")
    print("=" * 60)
    for col in metri_cols:
        print(f"{col:<40} {df[col].mean():.4f}")

    print("\nPer-question breakdown:")
    print("=" * 60)
    for _, row in df.iterrows():
        q = row["user_input"][:50]
        scores = {col: f"{row[col]:.2f}" for col in metri_cols}
        print(f"{q:<50} {scores}")

    output_path = RESULTS_PATH.parent / "ragas_scores.json"
    df.to_json(output_path, orient="records", indent=2)
    print(f"\nFull result saved to : {output_path}")

def main():
    print("=" * 60)
    print("Phase 3 — RAGAS Evaluation")
    print("=" * 60)

    if not RESULTS_PATH.exists():
        print(f"EEROR: {RESULTS_PATH} not found. Run run_eval.py first.")
        sys.exit(1)

    evaluator_llm = build_evaluator_llm()
    faithfulness = Faithfulness(llm=evaluator_llm)
    context_precision = LLMContextPrecisionWithReference(llm = evaluator_llm)
    context_recall = LLMContextRecall(llm = evaluator_llm)
    metrics = [faithfulness, context_precision, context_recall]

    dataset = load_dataset(RESULTS_PATH)

    print("\nRunning RAGAS - this will make several llm calls...\n")
    results = evaluate(dataset = dataset, metrics= metrics)
    print_results(results)

if __name__ == "__main__" :
    main()