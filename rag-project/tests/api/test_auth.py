import hashlib

import pytest

import config
from api.main import _validate_api_key_config, app, lifespan


def test_missing_header_is_401(client):
    assert client.post("/query", json={"query": "q"}).status_code == 401


@pytest.mark.parametrize("header", ["Basic abc", "Bearer", "token abc", ""])
def test_malformed_header_is_401(client, header):
    r = client.post("/query", json={"query": "q"}, headers={"Authorization": header})
    assert r.status_code == 401


def test_wrong_key_is_401(client):
    r = client.post(
        "/query", json={"query": "q"}, headers={"Authorization": "Bearer nope"}
    )
    assert r.status_code == 401
    assert "Invalid API key" in r.json()["detail"]


def test_non_ascii_key_is_401_not_500(client):
    r = client.post(
        "/query",
        json={"query": "q"},
        headers={"Authorization": "Bearer café-key".encode("latin-1")},
    )
    assert r.status_code == 401


def test_unset_server_key_rejects_requests_with_401_not_500(client, monkeypatch):
    monkeypatch.delenv(config.API_KEY, raising=False)
    r = client.post(
        "/query", json={"query": "q"}, headers={"Authorization": "Bearer anything"}
    )
    assert r.status_code == 401


def test_empty_server_key_does_not_accept_an_empty_bearer(client, monkeypatch):
    monkeypatch.setenv(config.API_KEY, "")
    r = client.post("/query", json={"query": "q"}, headers={"Authorization": "Bearer "})
    assert r.status_code == 401


def test_valid_key_returns_its_hash_for_per_key_limits(api_key):
    from api.core.auth import verify_api_key

    assert (
        verify_api_key(f"Bearer {api_key}")
        == hashlib.sha256(api_key.encode()).hexdigest()
    )


@pytest.mark.parametrize("value", [None, "", "short-key"])
def test_startup_refuses_a_missing_or_short_key(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(config.API_KEY, raising=False)
    else:
        monkeypatch.setenv(config.API_KEY, value)
    with pytest.raises(RuntimeError, match="API_KEY"):
        _validate_api_key_config()


def test_startup_accepts_a_strong_key(api_key):
    _validate_api_key_config()


def test_lifespan_aborts_before_loading_models_when_key_is_unset(monkeypatch):
    import asyncio
    import logging.config

    monkeypatch.delenv(config.API_KEY, raising=False)
    monkeypatch.setattr(logging.config, "dictConfig", lambda cfg: None)

    async def enter():
        async with lifespan(app):
            pass

    with pytest.raises(RuntimeError, match="API_KEY"):
        asyncio.run(enter())


def test_health_needs_no_auth(client):
    assert client.get("/health").status_code == 200
