from src.llm import client


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": " ok "}}]}


def test_llm_calls_reuse_one_pooled_session(monkeypatch):
    key_env = client._resolve_provider("groq")[3]
    monkeypatch.setenv(key_env, "test-key")

    urls = []

    def fake_post(url, **kwargs):
        urls.append(url)
        return FakeResponse()

    monkeypatch.setattr(client._session, "post", fake_post)

    assert client.call_llm("q", provider="groq") == "ok"
    assert client.call_llm("q", provider="groq") == "ok"
    assert len(urls) == 2


def test_model_override_replaces_the_pipeline_model(monkeypatch):
    monkeypatch.setenv(client._resolve_provider("groq")[3], "test-key")
    sent = []
    monkeypatch.setattr(
        client._session,
        "post",
        lambda url, **kw: sent.append(kw["json"]) or FakeResponse(),
    )

    client.call_llm("q", provider="groq")
    client.call_llm("q", provider="groq", model="qwen/qwen3.8-27b")
    assert sent[0]["model"] == client.model_name("groq")
    assert sent[1]["model"] == "qwen/qwen3.8-27b"


def test_missing_provider_counts_are_estimated_and_labelled(monkeypatch):
    """Ollama omits prompt_eval_count on a KV-cache hit; that half must say 'estimated'."""
    from prometheus_client import REGISTRY

    from src.llm import usage

    class OllamaResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "ok"}, "eval_count": 3}

    monkeypatch.setattr(client._session, "post", lambda url, **kw: OllamaResponse())
    model = client.model_name("ollama")

    def sample(kind, source):
        labels = {"stage": "rewrite", "provider": "ollama", "model": model}
        return (
            REGISTRY.get_sample_value(
                "llm_tokens_total", {**labels, "type": kind, "source": source}
            )
            or 0.0
        )

    before = sample("prompt", "estimated")
    with usage.track() as calls:
        client.call_llm("x" * 400, provider="ollama", stage="rewrite")

    [call] = calls
    assert (call["prompt_tokens"], call["prompt_source"]) == (100, "estimated")
    assert (call["completion_tokens"], call["completion_source"]) == (3, "reported")
    assert sample("prompt", "estimated") == before + 100
    assert sample("completion", "reported") >= 3
