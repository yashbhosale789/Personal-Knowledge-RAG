import json
import sys
from collections import Counter

from eval.paths import GOLDEN_PATH as PATH

golden = json.loads(PATH.read_text(encoding="utf-8"))
if any(i["split"] == "test" for i in golden):
    sys.exit("test split already assigned; refusing to reassign")

seen = Counter()
for item in golden:
    item["split"] = "test" if seen[item["category"]] % 4 == 3 else "dev"
    seen[item["category"]] += 1

PATH.write_text(
    json.dumps(golden, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)
print(Counter(i["split"] for i in golden))
