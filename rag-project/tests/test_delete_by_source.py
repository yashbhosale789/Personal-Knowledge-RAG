# test_delete_by_source.py — run with: python -m test_delete_by_source
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vectorstore.store import delete_by_source, add_chunks
from langchain_core.documents import Document

# no matching source -> 0, no exception
assert delete_by_source("/nonexistent/path.pdf") == 0

# real chunk -> delete finds it, second delete finds nothing
test_path = "./data/documents/something.pdf"
add_chunks(
    [
        Document(
            page_content="test content",
            metadata={"source": test_path, "filename": test_path},
        )
    ]
)
assert delete_by_source(test_path) == 1
assert delete_by_source(test_path) == 0  # already gone

print("delete_by_source: OK")
