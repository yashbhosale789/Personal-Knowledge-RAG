import ast
import hashlib
import json
from pathlib import Path

import config
from eval.paths import ROOT

CODE_DIRS = ("src/pipeline", "src/retrieval", "src/llm")
CONFIG_KEYS = (
    "PIPELINE_PROVIDER",
    "EVAL_PROVIDER",
    "GROQ_PIPELINE_MODEL",
    "OPENROUTER_MODEL",
    "GEMINI_PIPELINE_MODEL",
    "REWRITE_SYSTEM",
    "SYSTEM_PROMPT",
    "CITATION_VERIFIER_SYSTEM",
    "SUFFICIENCY_JUDGE_SYSTEM",
    "ANSWER_TEMPLATE",
    "ABSTAIN_MESSAGE",
    "SUFFICIENCY_CE_FLOOR",
    "TOP_K",
    "RRF_K",
    "RERANKER_MODEL",
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "EMBEDDINGS_MODEL_NAME",
)


def ast_hash(source: str) -> str:
    return hashlib.sha256(ast.dump(ast.parse(source)).encode()).hexdigest()


def code_hashes() -> dict[str, str]:
    files = sorted(p for d in CODE_DIRS for p in (ROOT / d).glob("*.py"))
    return {
        p.relative_to(ROOT).as_posix(): ast_hash(p.read_text(encoding="utf-8"))
        for p in files
    }


def fingerprint(overrides: dict | None = None) -> str:
    parts = {
        "code": code_hashes(),
        "config": {k: getattr(config, k) for k in CONFIG_KEYS},
        "chunks": hashlib.sha256(config.CHUNKS_PATH.read_bytes()).hexdigest(),
        "overrides": overrides or {},
    }
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:10]


def context_hash(contexts: list[str]) -> str:
    return hashlib.sha256("\x00".join(contexts).encode()).hexdigest()[:10]


def key(variant: str, qid: str, fp: str) -> str:
    return f"{variant}|{qid}|{fp}"


def load(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    records: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue  # a torn final line from a crash; that key simply gets redone
        records[record["key"]] = record
    return records


def append(path: Path, record: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def _selfcheck() -> None:
    assert ast_hash("x = 1  # note") == ast_hash("x   =   1")  # nosec B101
    assert ast_hash("x = 1") != ast_hash("x = 2")  # nosec B101
    assert (
        fingerprint() == fingerprint() != fingerprint({"reranker": "other"})
    )  # nosec B101
    assert context_hash(["a", "b"]) != context_hash(["b", "a"])  # nosec B101


if __name__ == "__main__":
    _selfcheck()
    print("fingerprint:", fingerprint())
