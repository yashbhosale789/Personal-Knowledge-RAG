import pytest

import config
from src.pipeline import citation_verification as cv

CHUNKS = [{"text": "Position the jack under the jacking point.", "metadata": {}}]


@pytest.fixture
def llm(monkeypatch):
    def install(reply):
        calls = []

        def fake(prompt, system=None, provider=None):
            calls.append({"prompt": prompt, "provider": provider})
            return reply

        monkeypatch.setattr(cv, "call_llm", fake)
        return calls

    return install


@pytest.mark.parametrize(
    "answer",
    [
        "Use the jack [SOURCE 1].",
        "x [source 2] y",
        "x [ SOURCE  3 ] y",
        "x 【SOURCE 1】 y",
    ],
)
def test_citation_markers_detected(answer):
    assert cv._has_citation(answer)


@pytest.mark.parametrize("answer", ["no markers", "see SOURCE 1", "[SOURCE]", "[1]"])
def test_missing_markers_not_detected(answer):
    assert not cv._has_citation(answer)


def test_answer_without_citations_is_rejected_without_calling_the_llm(llm):
    calls = llm('{"grounded": true, "reason": "r"}')
    result = cv.verify_citation("The jack goes somewhere.", CHUNKS)
    assert result["grounded"] is False
    assert result["tier"] == "no_citations"
    assert calls == []


def test_grounded_verdict_passes_through(llm):
    llm('{"grounded": true, "unsupported_claims": [], "reason": "ok"}')
    result = cv.verify_citation("Jack under the point [SOURCE 1].", CHUNKS)
    assert result == {
        "grounded": True,
        "unsupported_claims": [],
        "reason": "ok",
        "tier": "llm_judge",
    }


def test_unsupported_claims_are_reported(llm):
    llm(
        '{"grounded": false, "unsupported_claims": ["30cm behind"], "reason": "invented"}'
    )
    result = cv.verify_citation("30cm behind the wheel [SOURCE 1]", CHUNKS)
    assert result["grounded"] is False
    assert result["unsupported_claims"] == ["30cm behind"]


def test_verifier_uses_eval_provider_not_pipeline_provider(llm):
    calls = llm('{"grounded": true, "reason": "ok"}')
    cv.verify_citation("x [SOURCE 1]", CHUNKS)
    assert calls[0]["provider"] == config.EVAL_PROVIDER


@pytest.mark.parametrize("reply", ["not json", '{"reason": "missing grounded"}', "{}"])
def test_unparsable_verdict_fails_closed(llm, reply):
    llm(reply)
    result = cv.verify_citation("x [SOURCE 1]", CHUNKS)
    assert result["grounded"] is False
    assert result["tier"] == "llm_judge"


def test_prompt_numbers_the_sources(llm):
    calls = llm('{"grounded": true, "reason": "ok"}')
    two = CHUNKS + [{"text": "second chunk", "metadata": {}}]
    cv.verify_citation("x [SOURCE 1]", two)
    assert "[SOURCE 2]" in calls[0]["prompt"]
    assert "second chunk" in calls[0]["prompt"]
