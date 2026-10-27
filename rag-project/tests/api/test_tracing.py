"""Langfuse tracing (Phase 13.4): off without keys, one trace per /query keyed by the
request ID, content masked by default, never traced outside /query, and fail-open.
Offline: spans go to an in-memory exporter on a private TracerProvider."""

import json
import time
import uuid

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from api.routers import query as query_router
from src import tracing
from src.llm import client as llm_client
from src.observability import timed

from .conftest import pipeline_result

QUERY = "How do I tighten the lug nuts?"


class _LLMResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {
            "choices": [
                {"message": {"content": "Tighten in a star pattern [SOURCE 1]."}}
            ],
            "usage": {"prompt_tokens": 900, "completion_tokens": 40},
        }


def _install(
    monkeypatch, *, masked=False, exporter=None, base_url="http://127.0.0.1:9"
):
    from langfuse import Langfuse

    exporter = exporter or InMemorySpanExporter()
    langfuse = Langfuse(
        public_key=f"pk-lf-test-{uuid.uuid4().hex}",
        secret_key="sk-lf-test",
        base_url=base_url,
        span_exporter=exporter,
        tracer_provider=TracerProvider(),
        mask=tracing.mask if masked else None,
        timeout=1,
    )
    monkeypatch.setattr(tracing, "_client", langfuse)
    monkeypatch.setattr(tracing, "_initialised", True)
    return langfuse, exporter


@pytest.fixture
def pipeline_with_stages(fakes, monkeypatch):
    """A fake pipeline that runs real hooks: a nested timed() stage and a real call_llm."""
    monkeypatch.setenv(llm_client._resolve_provider("groq")[3], "test-key")
    monkeypatch.setattr(llm_client._session, "post", lambda url, **kw: _LLMResponse())

    def pipeline(query, provider, return_contexts):
        with timed("dense_retrieve") as obs:
            with timed("dense_embed"):
                pass
            obs.update(input=query, output=[{"source": "manual.pdf", "rank": 0}])
        llm_client.call_llm("prompt", provider=provider, stage="generate")
        return pipeline_result(llm_usage=None)

    monkeypatch.setattr(query_router, "_run_pipeline", pipeline)


def _spans(langfuse, exporter):
    langfuse.flush()
    return {s.name: s for s in exporter.get_finished_spans()}


def test_without_keys_tracing_is_off_and_query_is_unchanged(
    client, fakes, ready, auth_headers, monkeypatch
):
    import langfuse

    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.setattr(tracing, "_client", None)
    monkeypatch.setattr(tracing, "_initialised", False)

    def must_not_run(*a, **kw):
        raise AssertionError("no Langfuse client without keys")

    monkeypatch.setattr(langfuse, "Langfuse", must_not_run)
    r = client.post("/query", json={"query": QUERY}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["outcome"] == "answer"
    assert tracing._get_client() is None


def test_a_query_is_one_trace_keyed_by_its_request_id(
    client, ready, auth_headers, pipeline_with_stages, monkeypatch
):
    langfuse, exporter = _install(monkeypatch)
    r = client.post("/query", json={"query": QUERY}, headers=auth_headers)
    assert r.status_code == 200
    spans = _spans(langfuse, exporter)

    assert set(spans) == {
        "rag-query",
        "embed-query-for-cache",
        "lookup-semantic-cache",
        "run-rag-pipeline",
        "search-dense-index",
        "embed-query",
        "generate-answer",
        "store-in-cache",
    }
    trace_id = r.headers["X-Request-ID"].replace("-", "")
    assert {f"{s.context.trace_id:032x}" for s in spans.values()} == {trace_id}

    def parent(name):
        return spans[name].parent.span_id if spans[name].parent else None

    root = spans["rag-query"].context.span_id
    assert parent("run-rag-pipeline") == root
    assert parent("generate-answer") == spans["run-rag-pipeline"].context.span_id
    assert parent("embed-query") == spans["search-dense-index"].context.span_id

    attrs = {name: dict(s.attributes) for name, s in spans.items()}
    assert attrs["search-dense-index"]["langfuse.observation.type"] == "retriever"
    gen = attrs["generate-answer"]
    assert gen["langfuse.observation.type"] == "generation"
    assert json.loads(gen["langfuse.observation.usage_details"]) == {
        "input": 900,
        "output": 40,
    }
    assert QUERY in attrs["rag-query"]["langfuse.observation.input"]
    assert "Use the lug wrench" in attrs["rag-query"]["langfuse.observation.output"]


def test_content_is_masked_by_default_but_identifiers_stay_readable(
    client, ready, auth_headers, pipeline_with_stages, monkeypatch
):
    langfuse, exporter = _install(monkeypatch, masked=True)
    r = client.post("/query", json={"query": QUERY}, headers=auth_headers)
    exported = json.dumps(
        [dict(s.attributes) for s in _spans(langfuse, exporter).values()]
    )
    assert QUERY not in exported and "lug wrench" not in exported
    assert "[masked:" in exported
    assert r.headers["X-Request-ID"] in exported  # metadata.request_id is not masked


def test_nothing_is_traced_outside_a_query(monkeypatch):
    """Eval runs and scripts call the pipeline directly; they must cost no Langfuse units."""
    langfuse, exporter = _install(monkeypatch)
    monkeypatch.setenv(llm_client._resolve_provider("groq")[3], "test-key")
    monkeypatch.setattr(llm_client._session, "post", lambda url, **kw: _LLMResponse())
    with timed("rerank"):
        llm_client.call_llm("prompt", provider="groq", stage="generate")
    assert _spans(langfuse, exporter) == {}


class _FailingExporter(InMemorySpanExporter):
    def export(self, spans):
        raise ConnectionError("langfuse unreachable")


@pytest.mark.parametrize(
    "failure", ["exporter_raises", "sdk_raises", "unreachable_host"]
)
def test_tracing_failures_never_fail_or_slow_a_query(
    client, ready, auth_headers, pipeline_with_stages, monkeypatch, failure
):
    if failure == "unreachable_host":  # the real OTLP exporter, nothing listening
        from langfuse import Langfuse

        langfuse = Langfuse(
            public_key=f"pk-lf-test-{uuid.uuid4().hex}",
            secret_key="sk-lf-test",
            base_url="http://127.0.0.1:9",
            tracer_provider=TracerProvider(),
            timeout=1,
        )
        monkeypatch.setattr(tracing, "_client", langfuse)
        monkeypatch.setattr(tracing, "_initialised", True)
    else:
        langfuse, _ = _install(monkeypatch, exporter=_FailingExporter())
    if failure == "sdk_raises":

        def broken(*a, **kw):
            raise RuntimeError("SDK bug")

        monkeypatch.setattr(langfuse, "start_as_current_observation", broken)

    started = time.monotonic()
    r = client.post("/query", json={"query": QUERY}, headers=auth_headers)
    elapsed = time.monotonic() - started
    assert r.status_code == 200 and r.json()["outcome"] == "answer"
    assert elapsed < 1.0  # export is in the background; nothing waits on Langfuse
    langfuse.shutdown()
