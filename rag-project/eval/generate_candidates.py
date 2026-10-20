import json
import re
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from validate_dataset import (
    DIFFICULTIES,
    basename,
    check_span,
    load_chunks,
    norm,
)

from config import (
    CHUNKS_PATH,
    GC_DELAY,
    GC_SKIP_SOURCES,
    GC_SYSTEM,
)
from src.llm.client import call_llm

OUT_PATH = Path(__file__).parent / "candidates.jsonl"


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKC", text).lower())


def copies_chunk(question: str, chunk_text: str, n: int = 5) -> bool:
    q, c = words(question), words(chunk_text)
    grams = {tuple(c[i : i + n]) for i in range(len(c) - n + 1)}
    return any(tuple(q[i : i + n]) in grams for i in range(len(q) - n + 1))


def parse_json(raw: str) -> dict | None:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    try:
        return json.loads(match.group(0)) if match else None
    except json.JSONDecodeError:
        return None


def ask(prompt: str) -> str:
    for attempt in range(3):
        try:
            return call_llm(prompt, system=GC_SYSTEM)
        except Exception as e:
            if "429" not in str(e) or attempt == 2:
                raise
            time.sleep(60 * (attempt + 1))


def chunk_key(chunk: dict) -> str:
    return f"{basename(chunk['metadata']['source'])}#{chunk['metadata']['chunk_index']}"


def reject(key: str, reason: str) -> dict:
    return {"chunk_key": key, "status": "rejected", "reason": reason}


def draft(chunk: dict, chunks_norm: dict[str, list[str]]) -> dict:
    key, source = chunk_key(chunk), basename(chunk["metadata"]["source"])
    raw = ask(f"DOCUMENT: {source}\n\nCHUNK:\n{chunk['text']}")
    data = parse_json(raw)
    if data is None:
        return reject(key, f"unparseable output: {raw[:300]!r}")
    if data.get("skip"):
        return reject(key, f"skipped by model: {data.get('reason')}")
    question, truth, evidence, difficulty = (
        data.get(k) for k in ("question", "ground_truth", "evidence", "difficulty")
    )
    if not all(isinstance(v, str) and v.strip() for v in (question, truth, evidence)):
        return reject(key, "missing question, ground_truth or evidence")
    if difficulty not in DIFFICULTIES:
        return reject(key, "invalid or missing difficulty")
    errors, warnings = check_span({"source": source, "evidence": evidence}, chunks_norm)
    if errors:
        return reject(key, errors[0])
    if norm(evidence) not in norm(chunk["text"]):
        return reject(key, "evidence is not in this chunk")
    if norm(evidence) not in norm(chunk["text"]):
        return reject(key, "evidence is not in this chunk")
    if norm(evidence) not in norm(chunk["text"]):
        return reject(key, "evidence is not in this chunk")
    return {
        "chunk_key": key,
        "status": "ok",
        "warnings": warnings,
        "item": {
            "category": "normal",
            "difficulty": difficulty,
            "question": question.strip(),
            "ground_truth": truth.strip(),
            "expected_outcome": "answer",
            "relevant": [{"source": source, "evidence": evidence.strip()}],
            "origin": "synthetic",
            "split": "dev",
            "ci": False,
        },
    }


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    raw = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    chunks_norm = load_chunks()
    done = set()
    if OUT_PATH.exists():
        lines = OUT_PATH.read_text(encoding="utf-8").splitlines()
        done = {json.loads(line)["chunk_key"] for line in lines if line.strip()}
    todo = [
        c
        for c in raw
        if basename(c["metadata"]["source"]) not in GC_SKIP_SOURCES
        and chunk_key(c) not in done
    ]
    todo.sort(
        key=lambda c: (c["metadata"]["chunk_index"], basename(c["metadata"]["source"]))
    )
    todo = todo[:limit]
    print(f"{len(todo)} chunks to draft ({len(done)} already done)")
    for i, chunk in enumerate(todo, 1):
        record = draft(chunk, chunks_norm)
        record["chunk_text"] = chunk["text"]
        with open(OUT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(
            f"[{i}/{len(todo)}] {record['chunk_key']}: {record['status']} {record.get('reason', '')}"
        )
        time.sleep(GC_DELAY)


def _selfcheck() -> None:
    assert copies_chunk(
        "Pull over to a safe flat location now",
        "Pull over to a safe, flat location away from traffic",
    )  # nosec B101
    assert not copies_chunk(
        "Where should I stop to swap a flat?",
        "Pull over to a safe, flat location away from traffic",
    )  # nosec B101


if __name__ == "__main__":
    _selfcheck()
    main()
