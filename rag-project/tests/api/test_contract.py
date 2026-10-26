"""Pins the /query response contract so Phase 14 (frontend) and Phase 15 changes cannot drift silently.

If this fails, the public response shape changed. Decide deliberately, then run
    UPDATE_CONTRACT=1 python -m pytest tests/api/test_contract.py
which rewrites the snapshot and bumps `contract_version`; commit the snapshot diff.
"""

import json
import os
from pathlib import Path

from api.models.responses import QueryResponse

from .conftest import pipeline_result

SNAPSHOT = Path(__file__).parent.parent / "contracts" / "query_response.json"

REQUIRED_FIELDS = {
    "query_id": str,
    "query": str,
    "answer": str,
    "sources": list,
    "chunks_used": int,
    "provider": str,
    "latency_ms": float,
    "timestamp": str,
    "prompt_version": str,
}
OPTIONAL_FIELDS = {
    "rewritten_query": (str, type(None)),
    "sufficiency": (dict, type(None)),
    "citation_check": (dict, type(None)),
    "confidence": (str, type(None)),
    "outcome": (str, type(None)),
}


def _current() -> dict:
    return QueryResponse.model_json_schema()


def test_schema_matches_the_pinned_snapshot():
    current = _current()
    if os.getenv("UPDATE_CONTRACT") == "1":
        previous = (
            json.loads(SNAPSHOT.read_text(encoding="utf-8"))
            if SNAPSHOT.exists()
            else {}
        )
        if previous.get("schema") != current:
            version = previous.get("contract_version", 0) + 1
            SNAPSHOT.write_text(
                json.dumps({"contract_version": version, "schema": current}, indent=2)
                + "\n",
                encoding="utf-8",
            )
    pinned = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert current == pinned["schema"], (
        "QueryResponse changed. If intended, run UPDATE_CONTRACT=1 pytest "
        "tests/api/test_contract.py and commit the new snapshot (bumps contract_version)."
    )


def test_snapshot_declares_a_version():
    assert json.loads(SNAPSHOT.read_text(encoding="utf-8"))["contract_version"] >= 1


def test_required_fields_are_exactly_the_pinned_set():
    pinned = json.loads(SNAPSHOT.read_text(encoding="utf-8"))["schema"]
    assert set(pinned["required"]) == set(REQUIRED_FIELDS)


def test_live_answer_response_has_the_documented_shape(
    client, fakes, ready, auth_headers
):
    body = client.post(
        "/query", json={"query": "lug nuts?"}, headers=auth_headers
    ).json()

    assert set(body) == set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)
    for name, kind in REQUIRED_FIELDS.items():
        assert isinstance(body[name], kind), name
    for name, kinds in OPTIONAL_FIELDS.items():
        assert isinstance(body[name], kinds), name
    assert all(isinstance(s, str) for s in body["sources"])
    assert set(body["sufficiency"]) == {"sufficient", "reason", "tier"}
    assert set(body["citation_check"]) == {
        "grounded",
        "unsupported_claims",
        "reason",
        "tier",
    }
    assert isinstance(body["citation_check"]["unsupported_claims"], list)


def test_live_abstain_response_has_the_same_top_level_keys(
    client, fakes, ready, auth_headers
):
    fakes.result = pipeline_result(
        outcome="abstain", citation_check=None, confidence=None
    )
    body = client.post(
        "/query", json={"query": "weather?"}, headers=auth_headers
    ).json()
    assert set(body) == set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)
    assert body["citation_check"] is None and body["confidence"] is None


def test_cached_response_has_the_same_top_level_keys(
    client, fakes, ready, auth_headers
):
    fakes.cached = {"answer": "a", "provider": "groq", "query": "q", "similarity": 1.0}
    body = client.post(
        "/query", json={"query": "lug nuts?"}, headers=auth_headers
    ).json()
    assert set(body) == set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)
    assert body["outcome"] == "cached"
