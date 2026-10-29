import pytest

from api.core.exceptions import ProviderError
from api.routers import query as query_router

from .conftest import pipeline_result


def post(client, auth_headers, **body):
    body.setdefault("query", "How do I tighten the lug nuts?")
    return client.post("/query", json=body, headers=auth_headers)


# --- health ----------------------------------------------------------------


def test_health_reports_degraded_until_the_pipeline_is_ready(client):
    body = client.get("/health").json()
    assert body["status"] == "degraded"
    assert body["pipeline_ready"] is False


def test_health_reports_ok_when_ready(client, ready):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["pipeline_ready"] is True
    assert set(body) == {"status", "version", "pipeline_ready", "timestamp"}


def test_metrics_endpoint_exposes_prometheus_text(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text


# --- validation ------------------------------------------------------------


def test_empty_query_is_422(client, fakes, ready, auth_headers):
    assert post(client, auth_headers, query="").status_code == 422


def test_overlong_query_is_422(client, fakes, ready, auth_headers):
    assert post(client, auth_headers, query="x" * 2001).status_code == 422


def test_unknown_provider_is_422(client, fakes, ready, auth_headers):
    assert post(client, auth_headers, provider="nonsense").status_code == 422


def test_missing_query_field_is_422(client, fakes, ready, auth_headers):
    assert client.post("/query", json={}, headers=auth_headers).status_code == 422


def test_whitespace_only_query_is_400(client, fakes, ready, auth_headers):
    r = post(client, auth_headers, query="   ")
    assert r.status_code == 400
    assert fakes.pipeline_calls == []


def test_not_ready_pipeline_is_503(client, fakes, auth_headers):
    r = post(client, auth_headers)
    assert r.status_code == 503
    assert fakes.pipeline_calls == []


# --- success path ----------------------------------------------------------


def test_answer_response_carries_the_pipeline_result(
    client, fakes, ready, auth_headers
):
    r = post(client, auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "Use the lug wrench [SOURCE 1]."
    assert body["sources"] == ["manual.pdf"]
    assert body["chunks_used"] == 3
    assert body["rewritten_query"] == "lug wrench"
    assert body["outcome"] == "answer"
    assert body["confidence"] == "high"
    assert body["citation_check"]["grounded"] is True
    assert body["sufficiency"]["sufficient"] is True
    assert body["query"] == "How do I tighten the lug nuts?"
    assert body["latency_ms"] >= 0


def test_query_id_matches_the_request_id_header(client, fakes, ready, auth_headers):
    r = post(client, auth_headers)
    assert r.json()["query_id"] == r.headers["X-Request-ID"]
    assert r.json()["query_id"] != "unknown"


def test_each_request_gets_its_own_id(client, fakes, ready, auth_headers):
    a = post(client, auth_headers).json()["query_id"]
    b = post(client, auth_headers).json()["query_id"]
    assert a != b


def test_query_is_trimmed_before_the_pipeline_sees_it(
    client, fakes, ready, auth_headers
):
    post(client, auth_headers, query="  lug nuts  ")
    assert fakes.pipeline_calls[0]["query"] == "lug nuts"


def test_provider_override_is_used_and_reported(client, fakes, ready, auth_headers):
    r = post(client, auth_headers, provider="gemini")
    assert fakes.pipeline_calls[0]["provider"] == "gemini"
    assert r.json()["provider"] == "gemini"


def test_answers_are_cached(client, fakes, ready, auth_headers):
    post(client, auth_headers)
    assert len(fakes.cache_writes) == 1
    assert fakes.cache_writes[0][1] == "Use the lug wrench [SOURCE 1]."


def test_cache_miss_embeds_the_query_once(client, fakes, ready, auth_headers):
    post(client, auth_headers)
    assert fakes.embeddings == ["How do I tighten the lug nuts?"]
    assert fakes.cache_writes[0][3] == b"emb:How do I tighten the lug nuts?"


# --- abstention ------------------------------------------------------------


def test_abstention_is_reported_and_never_cached(client, fakes, ready, auth_headers):
    fakes.result = pipeline_result(
        answer="I don't have enough information in the knowledge base to answer this question accurately.",
        outcome="abstain",
        citation_check=None,
        confidence=None,
        sufficiency={"sufficient": False, "reason": "off topic", "tier": "score_floor"},
    )
    r = post(client, auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["outcome"] == "abstain"
    assert body["citation_check"] is None
    assert body["confidence"] is None
    assert body["sufficiency"]["sufficient"] is False
    assert fakes.cache_writes == []


def test_low_confidence_answer_is_reported(client, fakes, ready, auth_headers):
    fakes.result = pipeline_result(outcome="answer_low_confidence", confidence="low")
    body = post(client, auth_headers).json()
    assert body["outcome"] == "answer_low_confidence"
    assert body["confidence"] == "low"


# --- cache hit -------------------------------------------------------------


def test_cache_hit_skips_the_pipeline(client, fakes, ready, auth_headers):
    fakes.cached = {
        "answer": "cached answer",
        "provider": "groq",
        "query": "q",
        "similarity": 0.99,
    }
    r = post(client, auth_headers)
    body = r.json()
    assert body["outcome"] == "cached"
    assert body["answer"] == "cached answer"
    assert body["provider"] == "groq"
    assert body["sources"] == [] and body["chunks_used"] == 0
    assert fakes.pipeline_calls == []
    assert fakes.cache_writes == []


# --- failures --------------------------------------------------------------


def test_all_providers_failing_is_502(client, fakes, ready, auth_headers):
    fakes.error = ProviderError("down", provider="groq")
    r = post(client, auth_headers)
    assert r.status_code == 502


def test_first_provider_failing_falls_back(
    client, fakes, ready, auth_headers, monkeypatch
):
    calls = []

    def flaky(query, provider, return_contexts):
        calls.append(provider)
        if provider == "groq":
            raise RuntimeError("boom")
        return pipeline_result()

    monkeypatch.setattr(query_router, "_run_pipeline", flaky)
    r = post(client, auth_headers, provider="groq")
    assert r.status_code == 200
    assert r.json()["provider"] == "openrouter"
    assert calls[0] == "groq"


def test_get_on_a_post_route_is_405(client):
    assert client.get("/query").status_code == 405


# --- prompt version (Phase 13.2) ------------------------------------------


def test_prompt_version_and_llm_usage_are_in_the_query_log(
    client, fakes, ready, auth_headers, caplog
):
    import json

    from config import PROMPT_VERSION

    with caplog.at_level("INFO", logger="api.routers.query"):
        body = post(client, auth_headers).json()

    assert body["prompt_version"] == PROMPT_VERSION
    events = [
        json.loads(r.getMessage())
        for r in caplog.records
        if r.name == "api.routers.query" and r.getMessage().startswith("{")
    ]
    assert len(events) == 1
    timing = {
        k: events[0].pop(k) for k in ("latency_ms", "stages_ms", "unaccounted_ms")
    }
    assert len(events[0].pop("rewritten_query_hash")) == 12
    assert events == [
        {
            "event": "query",
            "request_id": body["query_id"],
            "outcome": "answer",
            "provider": "groq",
            "prompt_version": PROMPT_VERSION,
            "llm_usage": fakes.result["llm_usage"],  # Phase 13.3: per-stage usage
        }
    ]
    assert set(timing["stages_ms"]) == {"cache_embed", "cache_lookup", "cache_store"}


def test_cache_hit_reports_the_current_prompt_version(
    client, fakes, ready, auth_headers
):
    from config import PROMPT_VERSION

    fakes.cached = {"answer": "a", "provider": "groq", "query": "q", "similarity": 1.0}
    assert post(client, auth_headers).json()["prompt_version"] == PROMPT_VERSION


def test_cache_lookup_is_scoped_to_the_requested_provider(
    client, fakes, ready, auth_headers, monkeypatch
):
    lookups = []
    monkeypatch.setattr(
        query_router,
        "find_cached_answer",
        lambda q, provider, emb: lookups.append(provider),
    )
    post(client, auth_headers, provider="gemini")
    assert lookups == ["gemini"]


def test_metrics_expose_the_prompt_version(client):
    from config import PROMPT_VERSION

    assert f'version="{PROMPT_VERSION}"' in client.get("/metrics").text


def test_query_latency_has_the_10s_bucket_the_latency_slo_reads(
    client, fakes, ready, auth_headers
):
    """prometheus-rules.yml selects le="10.0"; renaming or dropping that bucket silently empties the SLO."""
    post(client, auth_headers)
    assert (
        'http_request_duration_seconds_bucket{le="10.0",method="POST",path="/query"}'
        in client.get("/metrics").text
    )


# --- request tracing (Phase 13.4) ------------------------------------------


def test_every_api_and_src_log_line_of_a_query_carries_its_request_id(
    client, fakes, ready, auth_headers, monkeypatch
):
    """The ID reaches a src/ logger in the pipeline's worker thread without being passed."""
    import io
    import json
    import logging

    from src.observability import JsonFormatter, RequestIdFilter

    def pipeline(query, provider, return_contexts):
        logging.getLogger("src.pipeline.advanced_rag").info("in the pipeline thread")
        return fakes.result

    monkeypatch.setattr(query_router, "_run_pipeline", pipeline)
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    handler.addFilter(lambda r: r.name.startswith(("api.", "src.")))
    root = logging.getLogger()
    level = root.level
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    try:
        r = post(client, auth_headers)
    finally:
        root.removeHandler(handler)
        root.setLevel(level)

    lines = [json.loads(line) for line in buf.getvalue().splitlines()]
    assert "in the pipeline thread" in [line.get("message") for line in lines]
    assert "query" in [line.get("event") for line in lines]
    assert "/query" in [line.get("path") for line in lines]  # api.access
    assert {line["request_id"] for line in lines} == {r.headers["X-Request-ID"]}


def test_named_stages_account_for_the_query_latency(
    client, fakes, ready, auth_headers, monkeypatch, caplog
):
    import json
    import time

    from src.llm import usage
    from src.observability import timed

    def pipeline(query, provider, return_contexts):
        with timed("dense_retrieve"):
            with timed("dense_embed"):
                time.sleep(0.05)
            time.sleep(0.05)
        with timed("rerank"):
            time.sleep(0.1)
        return pipeline_result(llm_usage=usage.summarize([]))

    monkeypatch.setattr(query_router, "_run_pipeline", pipeline)
    with caplog.at_level("INFO", logger="api.routers.query"):
        body = post(client, auth_headers).json()

    [event] = [
        json.loads(r.getMessage())
        for r in caplog.records
        if r.name == "api.routers.query" and r.getMessage().startswith("{")
    ]
    stages = event["stages_ms"]
    assert list(stages) == [
        "cache_embed",
        "cache_lookup",
        "dense_embed",
        "dense_retrieve",
        "rerank",
        "cache_store",
    ]
    # Self-time: the nested dense_embed is not counted again in dense_retrieve.
    assert 45 <= stages["dense_retrieve"] < 90
    assert event["latency_ms"] >= 200
    remainder = event["latency_ms"] - sum(stages.values())
    assert event["unaccounted_ms"] == pytest.approx(remainder, abs=0.2)
    assert 0 <= event["unaccounted_ms"] < 50
    assert body["latency_ms"] == pytest.approx(event["latency_ms"], abs=0.1)

    metrics = client.get("/metrics").text
    assert 'rag_stage_duration_seconds_count{stage="rerank"}' in metrics


def test_a_cache_hit_returns_the_grounding_of_the_original_answer(
    client, fakes, ready, auth_headers
):
    """Phase 13.4: a cited answer must not come back uncited from the cache."""
    from src.llm.semantic_cache import GROUNDING_FIELDS

    post(client, auth_headers)  # miss: the pipeline's grounding is stored
    stored = fakes.cache_writes[0][4]
    assert stored == {f: fakes.result[f] for f in GROUNDING_FIELDS}

    fakes.cached = {"answer": "a", "provider": "groq", "query": "q", "similarity": 0.97}
    fakes.cached["grounding"] = stored
    body = post(client, auth_headers).json()
    assert body["outcome"] == "cached"
    assert {f: body[f] for f in GROUNDING_FIELDS} == stored


# --- RAG quality signals (Phase 13.4 step 3) --------------------------------


@pytest.mark.parametrize(
    "outcome, cached",
    [
        ("answer", True),
        ("answer_low_confidence", True),
        ("abstain", False),
        ("empty", False),
    ],
)
def test_each_outcome_is_counted_and_only_answers_are_cached(
    client, fakes, ready, auth_headers, outcome, cached
):
    from prometheus_client import REGISTRY

    def count():
        labels = {"outcome": outcome}
        return REGISTRY.get_sample_value("rag_query_outcomes_total", labels) or 0

    fakes.result = pipeline_result(outcome=outcome)
    before = count()
    assert post(client, auth_headers).json()["outcome"] == outcome
    assert count() == before + 1
    assert bool(fakes.cache_writes) is cached


def test_answer_is_served_but_not_cached_when_the_verifier_was_unavailable(
    client, fakes, ready, auth_headers
):
    check = {
        "grounded": False,
        "unsupported_claims": [],
        "reason": "x",
        "tier": "verifier_error",
    }
    fakes.result = pipeline_result(
        outcome="answer_low_confidence", confidence="low", citation_check=check
    )
    body = post(client, auth_headers).json()
    assert body["outcome"] == "answer_low_confidence"
    assert body["citation_check"]["tier"] == "verifier_error"
    assert fakes.cache_writes == []


def test_query_log_records_cache_similarity_on_a_hit_and_a_rewrite_hash_on_a_miss(
    client, fakes, ready, auth_headers, caplog
):
    """For the Phase 15.3 cache-layer decision."""
    import hashlib
    import json

    from prometheus_client import REGISTRY

    def events():
        return [
            json.loads(r.getMessage())
            for r in caplog.records
            if r.name == "api.routers.query" and r.getMessage().startswith("{")
        ]

    with caplog.at_level("INFO", logger="api.routers.query"):
        post(client, auth_headers)  # miss
        hits = REGISTRY.get_sample_value(
            "rag_query_outcomes_total", {"outcome": "cached"}
        )
        q = "How do I tighten the lug nuts?"
        fakes.cached = {
            "answer": "a",
            "provider": "groq",
            "query": q,
            "similarity": 0.98765,
        }
        post(client, auth_headers)  # verbatim repeat
        fakes.cached = {
            **fakes.cached,
            "query": "lug nut tightening?",
            "similarity": 0.93,
        }
        post(client, auth_headers)  # paraphrase

    miss, repeat, paraphrase = events()
    expected = hashlib.sha256(b"lug wrench").hexdigest()[:12]  # fake rewrite
    assert miss["rewritten_query_hash"] == expected
    assert "cache_similarity" not in miss
    assert (repeat["cache_similarity"], repeat["cache_exact_repeat"]) == (0.9877, True)
    assert (paraphrase["cache_similarity"], paraphrase["cache_exact_repeat"]) == (
        0.93,
        False,
    )
    assert "rewritten_query_hash" not in repeat
    after = REGISTRY.get_sample_value("rag_query_outcomes_total", {"outcome": "cached"})
    assert after == (hits or 0) + 2
