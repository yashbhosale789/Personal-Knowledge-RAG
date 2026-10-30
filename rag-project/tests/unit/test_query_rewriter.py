"""condense_query: a follow-up plus chat history becomes one standalone question."""

from config import CONDENSE_SYSTEM
from src.pipeline import query_rewriter as qr

HISTORY = [
    {
        "query": "Tell me about the SUV",
        "rewritten_query": None,
        "answer": "The SUV seats 7.",
    },
    {
        "query": "And the tyres?",
        "rewritten_query": "SUV tyre size",
        "answer": "It uses 18-inch tyres [SOURCE 2].",
    },
]


def fake_llm(monkeypatch, reply):
    sent = []

    def call_llm(prompt, system, provider, stage):
        sent.append({"prompt": prompt, "system": system, "stage": stage})
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(qr, "call_llm", call_llm)
    return sent


def test_history_goes_in_oldest_first_with_the_latest_message_last(monkeypatch):
    sent = fake_llm(monkeypatch, "  What tyre pressure does the SUV need?\n")

    assert (
        qr.condense_query("What pressure?", HISTORY)
        == "What tyre pressure does the SUV need?"
    )
    [call] = sent
    assert call["system"] == CONDENSE_SYSTEM and call["stage"] == "rewrite"
    prompt = call["prompt"]
    assert prompt.index("Tell me about the SUV") < prompt.index("And the tyres?")
    assert "(standalone: SUV tyre size)" in prompt
    assert "18-inch tyres" in prompt
    assert prompt.endswith("Latest message: What pressure?")


def test_a_failed_call_returns_none(monkeypatch):
    fake_llm(monkeypatch, RuntimeError("rate limited"))
    assert qr.condense_query("What pressure?", HISTORY) is None


def test_an_empty_or_answer_length_reply_returns_none(monkeypatch):
    fake_llm(monkeypatch, "   ")
    assert qr.condense_query("What pressure?", HISTORY) is None
    fake_llm(monkeypatch, "The pressure is 2.4 bar. " * 30)
    assert qr.condense_query("What pressure?", HISTORY) is None
