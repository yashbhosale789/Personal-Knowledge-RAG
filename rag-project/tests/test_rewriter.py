# test_rewriter.py — temporary

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from src.pipeline.query_rewriter import rewrite_query

query = "Where is the spare tyre located in an Aventro Sedan?"
rewritten = rewrite_query(query)
print(f"Original:  {query}")
print(f"Rewritten: {rewritten}")
