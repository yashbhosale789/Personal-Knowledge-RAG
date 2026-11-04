import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from config import CHUNKS_PATH, DATA_DIR, STORAGE_DIR
from src.ingestion.ingest import IngestRejected, index_changed, ingest_file

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


def save_chunks(chunks: list, path: Path) -> None:
    """Eval export only (corpus id, dataset validation); serving never reads it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [
        {"text": chunk.page_content, "metadata": chunk.metadata} for chunk in chunks
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> int:
    """Ingests every PDF in DATA_DIR through the shared path. Returns the number of
    failures (rejected files, or no documents at all)."""
    print(f"Loading documents from : {DATA_DIR}")

    # Sorted: the same order on every OS, so chunks.json (and the corpus id) is stable.
    # key=str: Windows Path ordering is case-insensitive, Linux is not.
    files = sorted(
        (p for p in DATA_DIR.rglob("*") if p.suffix.lower() == ".pdf"), key=str
    )
    if not files:
        print("No documents found. Add files to data/documents/ and retry. Exiting.")
        return 1

    chunks, rejected = [], []
    try:
        for path in files:
            try:
                chunks.extend(ingest_file(path, notify=False))
            except IngestRejected as e:
                print(f"[REJECTED] {path.name}: {e}")
                rejected.append(path.name)
    finally:
        index_changed()  # once per run, also after a crash mid-loop

    save_chunks(chunks, CHUNKS_PATH)
    print(f"[OK] Chunks saved to : {CHUNKS_PATH}")

    print("\nIngestion complete.")
    print(f"   Files ingested   : {len(files) - len(rejected)} of {len(files)}")
    print(f"   Chunks produced  : {len(chunks)}")
    print(f"   Stored in : {STORAGE_DIR}")
    if rejected:
        print(f"[FAIL] Rejected: {', '.join(rejected)}")
    return len(rejected)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
