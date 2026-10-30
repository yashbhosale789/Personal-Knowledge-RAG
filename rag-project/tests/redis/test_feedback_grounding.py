import uuid

import config
from src import feedback
from src.llm.rate_limiter import is_rate_limited


def test_grounding_round_trips_with_a_24h_ttl(client):
    request_id = str(uuid.uuid4())
    grounding = {"query": "q", "answer": "a", "chunks": [{"n": 1, "cited": True}]}
    feedback.save_grounding(request_id, grounding)
    key = config.FEEDBACK_GROUNDING_PREFIX + request_id
    try:
        assert feedback.load_grounding(request_id) == grounding
        assert 0 < client.ttl(key) <= config.FEEDBACK_GROUNDING_TTL_SECONDS
    finally:
        client.delete(key)


def test_expired_or_unknown_grounding_is_none(client):
    assert feedback.load_grounding(str(uuid.uuid4())) is None


def test_feedback_rate_limit_is_enforced(client):
    key = f"test-{uuid.uuid4().hex}"
    limit = config.RATE_LIMIT_PER_MINUTE["feedback"]
    assert not any(is_rate_limited(key, "feedback") for _ in range(limit))
    assert is_rate_limited(key, "feedback") is True
