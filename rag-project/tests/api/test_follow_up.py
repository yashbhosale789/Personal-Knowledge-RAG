"""Chat memory: a follow-up is rewritten into a standalone question before the cache and the pipeline."""

import pytest

from .conftest import pipeline_result

STANDALONE = "What torque do the lug nuts need?"
HISTORY = [
    {
        "query": "How do I change a tyre?",
        "rewritten_query": "change a tyre",
        "answer": "Loosen the lug nuts [SOURCE 1].",
    }
]


def ask(client, auth_headers, history=HISTORY, path="/query"):
    return client.post(
        path,
        json={"query": "And how tight?", "history": history},
        headers=auth_headers,
    )


def test_no_history_skips_the_rewrite(client, fakes, ready, auth_headers):
    r = ask(client, auth_headers, history=[])
    assert r.status_code == 200
    assert fakes.condense_calls == []
    assert fakes.cache_lookups == ["And how tight?"]
    assert fakes.pipeline_calls[0]["rewritten"] is None


@pytest.mark.parametrize("path", ["/query", "/query/stream"])
def test_follow_up_is_asked_and_cached_as_the_standalone_question(
    client, fakes, ready, auth_headers, path
):
    r = ask(client, auth_headers, path=path)
    assert r.status_code == 200

    assert fakes.condense_calls == [("And how tight?", HISTORY)]
    assert fakes.cache_lookups == [STANDALONE]
    call = fakes.pipeline_calls[0]
    # The standalone question replaces the pipeline's own rewrite: still one rewrite call.
    assert call["query"] == STANDALONE and call["rewritten"] == STANDALONE
    assert fakes.cache_writes[0][0] == STANDALONE
    [grounding] = fakes.groundings.values()
    assert grounding["query"] == STANDALONE


def test_follow_up_cache_hit_reports_the_standalone_question(
    client, fakes, ready, auth_headers
):
    fakes.cached = {
        "answer": "110 Nm [SOURCE 1].",
        "provider": "groq",
        "similarity": 0.98,
        "query": STANDALONE,
        "grounding": {"sources": ["manual.pdf"], "chunks": []},
    }
    body = ask(client, auth_headers).json()
    assert body["outcome"] == "cached"
    assert body["query"] == "And how tight?"
    assert body["rewritten_query"] == STANDALONE
    assert fakes.pipeline_calls == []


@pytest.mark.parametrize("path", ["/query", "/query/stream"])
def test_failed_rewrite_answers_the_raw_follow_up_without_the_cache(
    client, fakes, ready, auth_headers, path
):
    fakes.standalone = None
    fakes.result = pipeline_result()

    assert ask(client, auth_headers, path=path).status_code == 200
    assert fakes.cache_lookups == []
    assert fakes.cache_writes == []
    # The pipeline's normal rewrite still runs on the raw words.
    assert fakes.pipeline_calls[0]["query"] == "And how tight?"
    assert fakes.pipeline_calls[0]["rewritten"] is None


@pytest.mark.parametrize(
    "history",
    [
        HISTORY * 6,  # more than HISTORY_TURNS
        [{**HISTORY[0], "chunks": [{"n": 1}]}],  # sources are not memory
        [{**HISTORY[0], "answer": "x" * 501}],  # answers arrive clipped
        [{"answer": "no question"}],
    ],
)
def test_history_is_validated(client, fakes, ready, auth_headers, history):
    assert ask(client, auth_headers, history=history).status_code == 422
    assert fakes.condense_calls == []
