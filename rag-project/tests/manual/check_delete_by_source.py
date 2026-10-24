# Manual check against the real store — run: python tests/manual/check_delete_by_source.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.documents import Document

from src.vectorstore.store import add_chunks, delete_by_source

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
