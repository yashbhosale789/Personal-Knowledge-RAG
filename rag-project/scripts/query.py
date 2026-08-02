import sys
from pathlib import Path
from src.retrieval.retriever import retrieve

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

def main():
    query = input ("Enter a Query: ").strip()
    if not query:
        print("No query entered.")
        return

    results = retrieve(query)

    print(f"\n[Search] Top {len(results)} retrieved chunks:\n")

    for i, doc in enumerate(results,1):
        print(
            f"[{i}] Source: {doc.metadata.get('filename', 'unknown')} | "
            f"Chunk: {doc.metadata.get('chunk_index', '?')}"
        )
        print(doc.page_content[:300])
        print("-" * 60)

if __name__ == "__main__":
    main()
