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
