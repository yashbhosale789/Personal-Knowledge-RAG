import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval_eval import match_matrix
from validate_dataset import DEFAULT_DATASET

from src.pipeline.advanced_rag import retrieve_context

qid, *queries = sys.argv[1:]
item = next(
    i for i in json.loads(DEFAULT_DATASET.read_text(encoding="utf-8")) if i["id"] == qid
)

rewrites = json.loads(
    (Path(__file__).parent / "rewrites.json").read_text(encoding="utf-8")
)["rewrites"]
queries = queries or [rewrites[item["question"]]]

for query in queries:
    cells = []
    for stage, ranked in retrieve_context(query).items():
        ranks = [
            row.index(True) + 1 if True in row else None
            for row in match_matrix(item, ranked)
        ]
        cells.append(f"{stage}={ranks}")
    print(f"{query!r}\n   " + "  ".join(cells))
