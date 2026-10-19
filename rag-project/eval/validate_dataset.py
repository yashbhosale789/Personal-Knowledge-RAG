import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CHUNKS_PATH

DEFAULT_DATASET = Path(__file__).parent / "golden_dataset.json"

CATEGORIES = {
    "normal",
    "difficult",
    "multi_hop",
    "ambiguous",
    "unanswerable",
    "adversarial",
}
DIFFICULTIES = {"easy", "medium", "hard"}
OUTCOMES = {"answer", "abstain"}
ORIGINS = {"manual", "synthetic"}
SPLITS = {"dev", "test"}
ENUMS = {
    "category": CATEGORIES,
    "difficulty": DIFFICULTIES,
    "expected_outcome": OUTCOMES,
    "origin": ORIGINS,
    "split": SPLITS,
}
REQUIRED = set(ENUMS) | {"id", "question", "ground_truth", "relevant", "ci"}

MIN_SPAN, MAX_SPAN = 25, 300
MAX_MATCHES = 2


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"[\W_]+", "", text)


def basename(path: str) -> str:
    return re.split(r"[\\/]", path)[-1]


def load_chunks() -> dict[str, list[str]]:
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    by_source: dict[str, list[str]] = {}
    for chunk in raw:
        name = basename(chunk["metadata"]["source"])
        by_source.setdefault(name, []).append(norm(chunk["text"]))
    return by_source


def check_span(rel: dict, chunks: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    source, evidence = rel.get("source"), rel.get("evidence")
    if source not in chunks:
        return [f"unknown source {source!r}; known: {sorted(chunks)}"], []
    span = norm(evidence) if isinstance(evidence, str) else ""
    if not span:
        return ["empty evidence"], []
    matches = sum(span in chunk for chunk in chunks[source])
    if matches == 0:
        return [f"evidence matches no chunk of {source}: {evidence[:50]!r}"], []
    warnings = []
    if matches > MAX_MATCHES:
        warnings.append(f"evidence matches {matches} chunks in {source} (too generic?)")
    length = len(" ".join(evidence.split()))
    if not MIN_SPAN <= length <= MAX_SPAN:
        warnings.append(f"evidence length {length} outside {MIN_SPAN}-{MAX_SPAN}")
    return [], warnings


def check_item(
    item: dict, chunks: dict[str, list[str]], seen: set[str]
) -> tuple[list[str], list[str]]:
    qid = item.get("id", "?")
    errors: list[str] = []
    warnings: list[str] = []

    missing = REQUIRED - item.keys()
    if missing:
        return [f"{qid}: missing fields {sorted(missing)}"], warnings

    if qid in seen:
        errors.append("duplicate id")
    seen.add(qid)

    for field in ("question", "ground_truth"):
        if not str(item[field]).strip():
            errors.append(f"empty {field}")
    for field, allowed in ENUMS.items():
        if item[field] not in allowed:
            errors.append(f"{field}={item[field]!r} not in {sorted(allowed)}")

    relevant, outcome, category = (
        item["relevant"],
        item["expected_outcome"],
        item["category"],
    )
    if outcome == "abstain" and relevant:
        errors.append("abstain items must have relevant=[]")
    if outcome == "answer" and not relevant:
        errors.append("answer items need at least one relevant span")
    if category == "unanswerable" and outcome != "abstain":
        errors.append("unanswerable items must expect abstain")
    if category == "multi_hop" and len(relevant) < 2:
        errors.append("multi_hop items need at least 2 spans")

    for rel in relevant:
        span_errors, span_warnings = check_span(rel, chunks)
        errors += span_errors
        warnings += span_warnings
    return [f"{qid}: {m}" for m in errors], [f"{qid}: {m}" for m in warnings]


def _selfcheck() -> None:
    assert (
        norm("A ventro compart-\nment Tra\ufb03c") == "aventrocompartmenttraffic"
    )  # nosec B101
    assert norm("It\u2019s") == norm("It's") == "its"  # nosec B101
    assert (
        basename("D:\\a\\b c.pdf") == "b c.pdf" == basename("/a/b c.pdf")
    )  # nosec B101


def main() -> int:
    _selfcheck()
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATASET
    dataset = json.loads(path.read_text(encoding="utf-8"))
    chunks = load_chunks()

    seen: set[str] = set()
    errors: list[str] = []
    warnings: list[str] = []
    for item in dataset:
        item_errors, item_warnings = check_item(item, chunks, seen)
        errors += item_errors
        warnings += item_warnings

    ci_items = [i for i in dataset if i.get("ci")]
    if not ci_items:
        errors.append("dataset: no item has ci=true")
    elif not any(i.get("expected_outcome") == "abstain" for i in ci_items):
        warnings.append(
            "dataset: no abstain item in the CI subset (abstention gate is blind)"
        )

    print(f"{len(dataset)} questions from {path.name}")
    print("by category:", dict(Counter(i.get("category") for i in dataset)))
    print("by split:   ", dict(Counter(i.get("split") for i in dataset)))
    cited = Counter(r.get("source") for i in dataset for r in i.get("relevant", []))
    for source in sorted(chunks):
        print(f"  {source}: {cited[source]} spans, {len(chunks[source])} chunks")
        if cited[source] == 0:
            warnings.append(f"dataset: no question cites {source}")

    for message in warnings:
        print("WARN ", message)
    for message in errors:
        print("ERROR", message)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
