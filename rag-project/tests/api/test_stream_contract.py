"""Pins the POST /query/stream event format (Phase 14.1) so the frontend cannot drift silently.

If the snapshot test fails, the `final` event's shape changed. Decide deliberately, then run
    UPDATE_CONTRACT=1 python -m pytest tests/api/test_stream_contract.py
which rewrites the snapshot and bumps `contract_version`; commit the snapshot diff.
"""

import json
import os
from pathlib import Path

from api.core.exceptions import ProviderError
from api.models.responses import QueryResponse, QueryStreamFinal
from src.pipeline.confidence import CAVEAT_TEXT

from .conftest import pipeline_result

SNAPSHOT = Path(__file__).parent.parent / "contracts" / "query_stream_final.json"


def events(client, auth_headers, query="lug nuts?") -> list[tuple[str, dict]]:
    r = client.post("/query/stream", json={"query": query}, headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    parsed = []
    for block in r.text.strip().split("\n\n"):
        event_line, data_line = block.split("\n")
        assert event_line.startswith("event: ") and data_line.startswith("data: ")
        parsed.append((event_line[7:], json.loads(data_line[6:])))
    return parsed


def test_final_schema_matches_the_pinned_snapshot():
    current = QueryStreamFinal.model_json_schema()
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
    assert pinned["contract_version"] >= 1
    assert current == pinned["schema"], (
        "QueryStreamFinal changed. If intended, run UPDATE_CONTRACT=1 pytest "
        "tests/api/test_stream_contract.py and commit the new snapshot."
    )


def test_final_carries_every_query_field():
    assert set(QueryResponse.model_fields) < set(QueryStreamFinal.model_fields)


def test_answer_streams_as_tokens_then_one_final(client, fakes, ready, auth_headers):
    stream = events(client, auth_headers)

    *tokens, (name, final) = stream
    assert [n for n, _ in tokens] == ["token", "token"]
    assert "".join(t["text"] for _, t in tokens) == fakes.result["answer"]
    assert name == "final"
    assert set(final) == set(QueryStreamFinal.model_fields)
    assert final["answer"] == fakes.result["answer"]
    assert final["outcome"] == "answer"
    assert final["confidence"] == "high"
    assert final["caveat"] is None
    assert final["chunks"] == fakes.result["chunks"]
    # Same side effects as /query: cached, and grounded for feedback under the same ID.
    assert len(fakes.cache_writes) == 1
    assert list(fakes.groundings) == [final["query_id"]]


def test_low_confidence_final_carries_the_caveat(client, fakes, ready, auth_headers):
    fakes.result = pipeline_result(
        answer="Torque is 200 Nm [SOURCE 1]." + CAVEAT_TEXT,
        confidence="low",
        outcome="answer_low_confidence",
    )
    fakes.tokens = ["Torque is 200 Nm [SOURCE 1]."]

    *_, (name, final) = events(client, auth_headers)
    assert name == "final"
    assert final["caveat"] == CAVEAT_TEXT
    assert final["answer"].endswith(CAVEAT_TEXT)


def test_cache_hit_is_a_single_final_event(client, fakes, ready, auth_headers):
    chunks = pipeline_result()["chunks"]
    fakes.cached = {
        "answer": "Cached answer [SOURCE 1].",
        "provider": "groq",
        "similarity": 0.97,
        "query": "lug nuts?",
        "grounding": {
            "sources": ["manual.pdf"],
            "confidence": "high",
            "chunks": chunks,
        },
    }

    [(name, final)] = events(client, auth_headers)
    assert name == "final"
    assert final["outcome"] == "cached"
    assert final["answer"] == "Cached answer [SOURCE 1]."
    assert final["chunks"] == chunks
    assert fakes.pipeline_calls == []


def test_abstain_is_a_single_final_event(client, fakes, ready, auth_headers):
    fakes.result = pipeline_result(
        answer="I don't have enough information.",
        outcome="abstain",
        confidence=None,
        citation_check=None,
    )
    fakes.tokens = []

    [(name, final)] = events(client, auth_headers)
    assert name == "final"
    assert final["outcome"] == "abstain"
    assert final["caveat"] is None
    assert fakes.cache_writes == []


def test_failure_before_any_token_is_a_single_error_event(
    client, fakes, ready, auth_headers
):
    fakes.error = ProviderError("down", provider="groq")

    [(name, error)] = events(client, auth_headers)
    assert name == "error"
    assert error["status"] == 502
    assert fakes.groundings == {}


def test_failure_after_tokens_does_not_fall_back(client, fakes, ready, auth_headers):
    fakes.tokens = ["Use the "]
    fakes.stream_error = RuntimeError("connection reset")

    stream = events(client, auth_headers)
    assert [n for n, _ in stream] == ["token", "error"]
    assert stream[1][1]["status"] == 502
    assert len(fakes.pipeline_calls) == 1  # no retry and no other provider re-streaming
    assert fakes.cache_writes == [] and fakes.groundings == {}


def test_requires_the_api_key(client, fakes, ready):
    r = client.post("/query/stream", json={"query": "lug nuts?"})
    assert r.status_code == 401


def test_query_contract_is_unchanged_by_the_stream_route(
    client, fakes, ready, auth_headers
):
    body = client.post(
        "/query", json={"query": "lug nuts?"}, headers=auth_headers
    ).json()
    assert set(body) == set(QueryResponse.model_fields)
