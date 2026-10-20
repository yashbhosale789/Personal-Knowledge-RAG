import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CHUNKS_PATH  # noqa: E402
from generate_candidates import chunk_key, words  # noqa: E402
from validate_dataset import DEFAULT_DATASET  # noqa: E402

CANDIDATES = Path(__file__).parent / "candidates.jsonl"
REVIEWED = Path(__file__).parent / "candidates_reviewed.jsonl"
DOC_PHRASES = re.compile(
    r"\b(listed|given|mentioned|according to|the (document|text|passage|guide|chunk))\b",
    re.I,
)


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def next_id(golden: list[dict]) -> str:
    return f"Q{max(int(i['id'][1:]) for i in golden) + 1:02d}"


def clean(item: dict) -> dict:
    for field in ("question", "ground_truth"):
        item[field] = item[field].replace("A ventro", "Aventro")
    return item


def flags(item: dict) -> list[str]:
    return (
        ["question refers to the document"]
        if DOC_PHRASES.search(item["question"])
        else []
    )


def hints(cand: dict, chunks: list[dict], n: int = 2) -> list[tuple[float, dict]]:
    item = cand["item"]
    target = {
        w for w in words(item["question"] + " " + item["ground_truth"]) if len(w) > 3
    }

    scored = [
        (len(target & set(words(c["text"]))) / max(len(target), 1), c)
        for c in chunks
        if chunk_key(c) != cand["chunk_key"]
    ]
    return sorted(scored, key=lambda s: s[0], reverse=True)[:n]


def main() -> None:
    golden = json.loads(DEFAULT_DATASET.read_text(encoding="utf-8"))
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    done = {r["chunk_key"] for r in load_jsonl(REVIEWED)}
    pending = [
        c
        for c in load_jsonl(CANDIDATES)
        if c["status"] == "ok" and c["chunk_key"] not in done
    ]
    print(f"{len(pending)} candidates to review")

    for n, cand in enumerate(pending, 1):
        item = clean(cand["item"])
        print(
            f"\n=== [{n}/{len(pending)}] {cand['chunk_key']} ({item['difficulty']}) ==="
        )
        print("CHUNK:", " ".join(cand["chunk_text"].split()))
        print("Q:", item["question"])
        print("GT:", item["ground_truth"])
        print("EVIDENCE:", item["relevant"][0]["evidence"])

        for flag in flags(item):
            print("FLAG:", flag)
        for score, chunk in hints(cand, chunks):
            print(
                f"ALSO? {score:.2f} {chunk_key(chunk)}: {' '.join(chunk['text'].split())[:110]}"
            )

        choice = ""
        while choice not in {"a", "d", "e", "r", "q"}:
            choice = (
                input("[a]ccept [d]ifficult+accept [e]dit+accept [r]eject [q]uit > ")
                .strip()
                .lower()
            )
        if choice == "q":
            break

        decision = "rejected"
        if choice in {"a", "d", "e"}:
            if choice == "d":
                item["category"] = "difficult"
            if choice == "e":
                for field in ("question", "ground_truth"):
                    new = input(f"new {field} (enter keeps): ").strip()
                    if new:
                        item[field] = new

            golden.append({"id": next_id(golden), **item})
            DEFAULT_DATASET.write_text(
                json.dumps(golden, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            decision = "accepted"

        with open(REVIEWED, "a", encoding="utf-8") as f:
            f.write(
                json.dumps({"chunk_key": cand["chunk_key"], "decision": decision})
                + "\n"
            )


if __name__ == "__main__":
    main()
