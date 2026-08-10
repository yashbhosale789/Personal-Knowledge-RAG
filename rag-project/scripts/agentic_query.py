# scripts/agentic_query.py

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent.react_agent import run_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)

logger = logging.getLogger(__name__)


def print_trajectory(trajectory: list[dict]) -> None:
    print("\n" + "=" * 60)
    print("AGENT TRAJECTORY")
    print("=" * 60)
    for step in trajectory:
        print(f"\n--- Iteration {step['iteration']} ---")
        print(step["raw"])
    print("\n" + "=" * 60)


def main() -> None:
    query = input("Enter your query: ").strip()
    if not query:
        print("No query entered. Exiting.")
        sys.exit(1)

    print(f"\nQuery: {query}")
    print("-" * 60)

    result = run_agent(query)

    print_trajectory(result["trajectory"])

    print("\nFINAL ANSWER")
    print("=" * 60)
    print(result["answer"])
    print(f"\nCompleted in {result['iterations']} iteration(s).")


if __name__ == "__main__":
    main()