import json
import sqlite3
import uuid

import pytest
import redis

import config
from api.routers import feedback as feedback_router
from src import feedback

from .conftest import pipeline_result

CHUNKS = [
    {
        "n": 1,
        "source": "manual.pdf",
        "page": "2",
        "snippet": "Use the wrench",
        "cited": True,
    }
]


@pytest.fixture
def store(fakes, tmp_path, monkeypatch):
    """Grounding comes from what /query saved (fakes.groundings); the SQLite file is per test."""
    db = tmp_path / "feedback.db"
    monkeypatch.setattr(config, "FEEDBACK_DB_PATH", db)
    monkeypatch.setattr(feedback, "load_grounding", fakes.groundings.get)
    monkeypatch.setattr(feedback_router, "is_rate_limited", lambda key, bucket: False)
    fakes.result = pipeline_result(chunks=CHUNKS)
    return db


def ask(client, auth_headers) -> str:
    r = client.post(
        "/query", json={"query": "How do I tighten the lug nuts?"}, headers=auth_headers
    )
    assert r.status_code == 200
    return r.json()["query_id"]


def rate(client, auth_headers, request_id, **body):
    return client.post(
        "/feedback",
        json={"request_id": request_id, "rating": "up", **body},
        headers=auth_headers,
    )


def rows(db) -> list[dict]:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM feedback")]
    finally:
        conn.close()


# --- round trip ------------------------------------------------------------


def test_feedback_is_stored_with_the_servers_grounding(
    client, ready, auth_headers, store
):
    request_id = ask(client, auth_headers)
    r = rate(client, auth_headers, request_id, rating="down", comment=" wrong page ")
    assert r.status_code == 200
    assert r.json() == {"status": "recorded", "request_id": request_id}

    (row,) = rows(store)
    assert row["request_id"] == request_id
    assert row["rating"] == "down"
    assert row["comment"] == "wrong page"
    assert row["query"] == "How do I tighten the lug nuts?"
    assert row["answer"] == "Use the lug wrench [SOURCE 1]."
    assert row["outcome"] == "answer"
    assert row["prompt_version"] == config.PROMPT_VERSION
    assert row["model"]
    assert json.loads(row["chunks"]) == CHUNKS


def test_cache_hit_saves_grounding_too(client, fakes, ready, auth_headers, store):
    fakes.cached = {
        "answer": "cached answer [SOURCE 1]",
        "provider": "groq",
        "query": "q",
        "similarity": 0.99,
        "grounding": {"chunks": CHUNKS},
    }
    request_id = ask(client, auth_headers)
    grounding = fakes.groundings[request_id]
    assert grounding["outcome"] == "cached"
    assert grounding["answer"] == "cached answer [SOURCE 1]"
    assert grounding["chunks"] == CHUNKS
    assert rate(client, auth_headers, request_id).status_code == 200


def test_abstain_saves_grounding(client, fakes, ready, auth_headers, store):
    fakes.result = pipeline_result(
        outcome="abstain", citation_check=None, chunks=CHUNKS
    )
    request_id = ask(client, auth_headers)
    assert fakes.groundings[request_id]["outcome"] == "abstain"


def test_resubmit_replaces_rating_and_comment(client, ready, auth_headers, store):
    request_id = ask(client, auth_headers)
    rate(client, auth_headers, request_id, rating="up", comment="good")
    first = rows(store)[0]
    r = rate(client, auth_headers, request_id, rating="down")
    assert r.status_code == 200
    (row,) = rows(store)
    assert row["rating"] == "down"
    assert row["comment"] is None
    assert row["created_at"] == first["created_at"]


# --- not found / store down ------------------------------------------------


def test_unknown_or_expired_request_id_is_404(client, ready, auth_headers, store):
    r = rate(client, auth_headers, str(uuid.uuid4()))
    assert r.status_code == 404
    assert not store.exists()


def test_redis_down_is_503_not_404(client, ready, auth_headers, store, monkeypatch):
    def down(request_id):
        raise redis.ConnectionError("down")

    monkeypatch.setattr(feedback, "load_grounding", down)
    assert rate(client, auth_headers, str(uuid.uuid4())).status_code == 503


# --- validation ------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {"request_id": "not-a-uuid", "rating": "up"},
        {"request_id": str(uuid.uuid4()), "rating": "meh"},
        {"request_id": str(uuid.uuid4())},
        {"rating": "up"},
        {
            "request_id": str(uuid.uuid4()),
            "rating": "up",
            "comment": "x" * (config.FEEDBACK_COMMENT_MAX_CHARS + 1),
        },
        # The client cannot supply the answer it is rating.
        {"request_id": str(uuid.uuid4()), "rating": "up", "answer": "forged"},
    ],
)
def test_invalid_body_is_422(client, ready, auth_headers, store, body):
    r = client.post("/feedback", json=body, headers=auth_headers)
    assert r.status_code == 422
    assert not store.exists()


def test_comment_at_the_cap_is_accepted(client, ready, auth_headers, store):
    request_id = ask(client, auth_headers)
    comment = "x" * config.FEEDBACK_COMMENT_MAX_CHARS
    assert rate(client, auth_headers, request_id, comment=comment).status_code == 200


# --- auth and rate limit ---------------------------------------------------


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer wrong-key"}, {"Authorization": "Basic abc"}],
)
def test_feedback_requires_the_api_key(client, ready, store, headers):
    r = client.post(
        "/feedback",
        json={"request_id": str(uuid.uuid4()), "rating": "up"},
        headers=headers,
    )
    assert r.status_code == 401
    assert not store.exists()


def test_rate_limited_feedback_is_429(client, ready, auth_headers, store, monkeypatch):
    seen = []

    def limited(key, bucket):
        seen.append(bucket)
        return True

    monkeypatch.setattr(feedback_router, "is_rate_limited", limited)
    request_id = ask(client, auth_headers)
    assert rate(client, auth_headers, request_id).status_code == 429
    assert seen == ["feedback"]
    assert not store.exists()
