"""advanced_rag: lazy singletons (F-05) and stage orchestration with every dependency faked."""

import importlib

import pytest
from langchain_core.documents import Document

import config
from src.pipeline import advanced_rag as ar
from src.pipeline.confidence import CAVEAT_TEXT

# --- lazy singletons (F-05) ------------------------------------------------


class _Explodes:
    def __init__(self, *args, **kwargs):
        raise AssertionError("model constructed at import time")


def test_importing_the_module_loads_no_models(monkeypatch):
    monkeypatch.setattr("src.retrieval.bm25_retriever.BM25Retriever", _Explodes)
    monkeypatch.setattr("src.retrieval.reranker.CrossEncoderReranker", _Explodes)
    try:
        importlib.reload(ar)
        assert ar._bm25 is None and ar._reranker is None
    finally:
        monkeypatch.undo()
        importlib.reload(ar)  # rebind the real classes for the rest of the session


class Counting:
    def __init__(self):
        self.built = 0

    def __call__(self):
        self.built += 1
        return object()


@pytest.fixture
def fresh(monkeypatch):
    bm25, reranker = Counting(), Counting()
    monkeypatch.setattr(ar, "_bm25", None)
    monkeypatch.setattr(ar, "_reranker", None)
    monkeypatch.setattr(ar, "BM25Retriever", bm25)
    monkeypatch.setattr(ar, "CrossEncoderReranker", reranker)
    return bm25, reranker


def test_getters_build_once_and_reuse(fresh):
    bm25, reranker = fresh
    assert ar.get_bm25() is ar.get_bm25()
    assert ar.get_reranker() is ar.get_reranker()
    assert (bm25.built, reranker.built) == (1, 1)


def test_nothing_is_built_until_asked(fresh):
    bm25, reranker = fresh
    assert (bm25.built, reranker.built) == (0, 0)


def test_warmup_builds_both(fresh):
    ar.warmup()
    assert tuple(c.built for c in fresh) == (1, 1)


def test_app_startup_warms_the_pipeline_singletons(monkeypatch):
    from api.main import _warmup_retrieval_component
    from src.embedding import embedder
    from src.vectorstore import store

    calls = []
    monkeypatch.setattr(
        embedder, "get_embedding_model", lambda: calls.append("embedder")
    )
    monkeypatch.setattr(store, "get_vectorstore", lambda: calls.append("store"))
    monkeypatch.setattr(ar, "warmup", lambda: calls.append("pipeline"))
    _warmup_retrieval_component()
    assert calls == ["embedder", "store", "pipeline"]


def test_injected_reranker_bypasses_the_singleton(monkeypatch):
    class Boom:
        def __call__(self):
            raise AssertionError("singleton must not be built")

    monkeypatch.setattr(ar, "_reranker", None)
    monkeypatch.setattr(ar, "CrossEncoderReranker", Boom())
    _stub_retrieval(monkeypatch)

    class Injected:
        def rerank(self, query, candidates):
            return candidates[:1]

    out = ar.retrieve_context("q", reranker=Injected())
    assert len(out["reranked"]) == 1


# --- retrieve_context ------------------------------------------------------


def _chunk(text, name="manual.pdf"):
    return {"text": text, "metadata": {"filename": name}, "score": 0.0, "rank": 0}


def _stub_retrieval(monkeypatch, dense=("d1", "shared"), sparse=("shared", "s1")):
    class FakeBM25:
        def retrieve(self, query, top_k):
            return [_chunk(t) for t in sparse]

    monkeypatch.setattr(ar, "_bm25", FakeBM25())
    monkeypatch.setattr(
        ar,
        "retrieve",
        lambda q, top_k: [
            Document(page_content=t, metadata={"filename": "manual.pdf"}) for t in dense
        ],
    )


def test_retrieve_context_returns_every_stage(monkeypatch):
    _stub_retrieval(monkeypatch)

    class Rev:
        def rerank(self, query, candidates):
            return list(reversed(candidates))

    out = ar.retrieve_context("q", reranker=Rev())
    assert set(out) == {"dense", "bm25", "fused", "reranked"}
    assert [c["text"] for c in out["dense"]] == ["d1", "shared"]
    assert out["fused"][0]["text"] == "shared"  # in both lists
    assert [c["text"] for c in out["reranked"]] == [
        c["text"] for c in reversed(out["fused"])
    ]


def test_dense_results_get_ranks(monkeypatch):
    _stub_retrieval(monkeypatch)
    out = ar.retrieve_context(
        "q", reranker=type("R", (), {"rerank": lambda s, q, candidates: candidates})()
    )
    assert [c["rank"] for c in out["dense"]] == [0, 1]


# --- prompt ----------------------------------------------------------------


def test_prompt_numbers_sources_and_fences_context_with_a_random_boundary():
    chunks = [_chunk("alpha text", "a.pdf"), _chunk("beta text", "b.pdf")]
    p1, p2 = (
        ar._build_prompt("the question", chunks),
        ar._build_prompt("the question", chunks),
    )
    assert "[SOURCE 1 - a.pdf]\nalpha text" in p1
    assert "[SOURCE 2 - b.pdf]\nbeta text" in p1
    assert p1.rstrip().endswith("ANSWER:")
    assert "QUESTION:\nthe question" in p1
    boundary = p1.split("===CONTEXT-")[1].split("===")[0]
    assert p1.count(f"===CONTEXT-{boundary}===") == 3
    assert p1 != p2  # boundary differs per call so a document cannot forge it


# --- run_advanced_rag_pipeline --------------------------------------------


class Wiring:
    def __init__(self):
        self.llm_calls = []
        self.reranked = [_chunk("Use the lug wrench.")]
        self.sufficiency = {"sufficient": True, "reason": "ok", "tier": "llm_judge"}
        self.answer = "Use the lug wrench [SOURCE 1]."
        self.grounded = True


@pytest.fixture
def wired(monkeypatch):
    w = Wiring()
    monkeypatch.setattr(ar, "rewrite_query", lambda q, provider=None: f"rewritten {q}")
    monkeypatch.setattr(
        ar,
        "retrieve_context",
        lambda q, top_k=5, reranker=None: {"reranked": w.reranked},
    )
    monkeypatch.setattr(
        ar, "check_sufficiency", lambda q, chunks, provider=None: w.sufficiency
    )

    def llm(prompt, system=None, provider=None, stage=None):
        w.llm_calls.append({"prompt": prompt, "provider": provider})
        return w.answer

    monkeypatch.setattr(ar, "call_llm", llm)
    monkeypatch.setattr(
        ar,
        "verify_citation",
        lambda answer, chunks: {
            "grounded": w.grounded,
            "unsupported_claims": [],
            "reason": "r",
            "tier": "llm_judge",
        },
    )
    return w


def test_happy_path_answers_with_high_confidence(wired):
    result = ar.run_advanced_rag_pipeline("how?", provider="groq")
    assert result["outcome"] == "answer"
    assert result["confidence"] == "high"
    assert result["answer"] == "Use the lug wrench [SOURCE 1]."
    assert result["sources"] == ["manual.pdf"]
    assert result["rewritten_query"] == "rewritten how?"
    assert wired.llm_calls[0]["provider"] == "groq"
    assert "contexts" not in result


def test_return_contexts_includes_chunk_text(wired):
    result = ar.run_advanced_rag_pipeline("how?", return_contexts=True)
    assert result["contexts"] == ["Use the lug wrench."]


def test_ungrounded_answer_gets_the_caveat_and_low_confidence_outcome(wired):
    wired.grounded = False
    result = ar.run_advanced_rag_pipeline("how?")
    assert result["outcome"] == "answer_low_confidence"
    assert result["confidence"] == "low"
    assert result["answer"].endswith(CAVEAT_TEXT)


def test_insufficient_context_abstains_without_calling_the_generator(wired):
    wired.sufficiency = {
        "sufficient": False,
        "reason": "off topic",
        "tier": "score_floor",
    }
    result = ar.run_advanced_rag_pipeline("weather?")
    assert result["outcome"] == "abstain"
    assert result["answer"] == config.ABSTAIN_MESSAGE
    assert wired.llm_calls == []
    assert "citation_check" not in result


def test_no_retrieved_chunks_short_circuits(wired):
    wired.reranked = []
    result = ar.run_advanced_rag_pipeline("anything")
    assert result["chunks_used"] == 0
    assert result["sources"] == []
    assert result["outcome"] == "empty"
    assert wired.llm_calls == []


def test_fullwidth_citation_brackets_are_normalised(wired):
    wired.answer = "Use the wrench 【SOURCE 1】."
    result = ar.run_advanced_rag_pipeline("how?")
    assert "[SOURCE 1]" in result["answer"]
    assert "【" not in result["answer"]


def test_a_precomputed_rewrite_is_not_recomputed(wired, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("rewrite_query must not run")

    monkeypatch.setattr(ar, "rewrite_query", boom)
    result = ar.run_advanced_rag_pipeline("how?", rewritten="given")
    assert result["rewritten_query"] == "given"


def test_sources_are_deduplicated_and_reduced_to_basenames(wired):
    wired.reranked = [
        _chunk("a", "/x/m.pdf"),
        _chunk("b", "/x/m.pdf"),
        _chunk("c", "/x/n.pdf"),
    ]
    assert ar.run_advanced_rag_pipeline("how?")["sources"] == ["m.pdf", "n.pdf"]


# --- token and latency accounting (Phase 13.3) -----------------------------


def test_every_llm_stage_reports_tokens_and_latency(monkeypatch):
    """Real rewrite/judge/generate/verify code; only retrieval and HTTP are faked."""
    from prometheus_client import REGISTRY

    from src.llm import client

    for name in ("groq", "openrouter", "gemini"):
        monkeypatch.setenv(client._resolve_provider(name)[3], "test-key")
    chunk = {**_chunk("Use the lug wrench."), "ce_score": 5.0}
    monkeypatch.setattr(
        ar, "retrieve_context", lambda q, top_k=5, reranker=None: {"reranked": [chunk]}
    )

    replies = {
        config.REWRITE_SYSTEM: "lug nuts",
        config.SUFFICIENCY_JUDGE_SYSTEM: '{"sufficient": true, "reason": "ok"}',
        config.SYSTEM_PROMPT: "Use the lug wrench [SOURCE 1].",
        config.CITATION_VERIFIER_SYSTEM: '{"grounded": true, "unsupported_claims": [], "reason": "ok"}',
    }

    class Reply:
        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [{"message": {"content": self.content}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 7},
            }

    monkeypatch.setattr(
        client._session,
        "post",
        lambda url, json, **kw: Reply(replies[json["messages"][0]["content"]]),
    )

    model = client.model_name("groq")
    labels = {"stage": "generate", "provider": "groq", "model": model}

    def sample(name, **extra):
        return REGISTRY.get_sample_value(name, {**labels, **extra}) or 0.0

    tokens_before = sample("llm_tokens_total", type="prompt", source="reported")
    calls_before = sample("llm_call_duration_seconds_count")

    result = ar.run_advanced_rag_pipeline("how do I tighten?", provider="groq")

    usage = result["llm_usage"]
    assert [c["stage"] for c in usage["calls"]] == [
        "rewrite",
        "sufficiency",
        "generate",
        "citation_verify",
    ]
    assert all(c["prompt_tokens"] == 100 and c["ms"] >= 0 for c in usage["calls"])
    assert usage["prompt_tokens"] == 400 and usage["completion_tokens"] == 28
    assert usage["estimated"] is False
    assert sample("llm_tokens_total", type="prompt", source="reported") == (
        tokens_before + 100
    )
    assert sample("llm_call_duration_seconds_count") == calls_before + 1
