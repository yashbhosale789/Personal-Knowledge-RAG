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


def test_streamed_reply_is_passed_on_piece_by_piece(monkeypatch):
    monkeypatch.setenv(client._resolve_provider("groq")[3], "test-key")
    lines = [
        ": keep-alive",
        'data: {"choices": [{"delta": {"role": "assistant"}}]}',
        'data: {"choices": [{"delta": {"content": " Lösen "}}]}',
        "",
        'data: {"choices": [{"delta": {"content": "[SOURCE 1]"}}]}',
        'data: {"choices": [], "usage": {"prompt_tokens": 7, "completion_tokens": 2}}',
        "data: [DONE]",
        'data: {"choices": [{"delta": {"content": "after done"}}]}',
    ]
    sent = {}

    class StreamResponse:
        encoding = None

        def raise_for_status(self):
            pass

        def iter_lines(self, decode_unicode):
            assert decode_unicode and self.encoding == "utf-8"
            return iter(lines)

    def fake_post(url, **kw):
        sent.update(kw)
        return StreamResponse()

    monkeypatch.setattr(client._session, "post", fake_post)
    pieces = []

    text = client.call_llm(
        "q", provider="groq", stage="generate", on_token=pieces.append
    )

    assert pieces == [" Lösen ", "[SOURCE 1]"]
    assert text == "Lösen [SOURCE 1]"
    assert sent["stream"] is True and sent["json"]["stream"] is True
