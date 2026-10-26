import pytest

import config

PROMPTS = (
    "REWRITE_SYSTEM",
    "SYSTEM_PROMPT",
    "ANSWER_TEMPLATE",
    "SUFFICIENCY_JUDGE_SYSTEM",
    "CITATION_VERIFIER_SYSTEM",
)


def _version(**edits) -> str:
    return config.prompt_version(*(edits.get(n, getattr(config, n)) for n in PROMPTS))


def test_prompt_version_is_the_hash_of_every_pipeline_prompt():
    assert config.PROMPT_VERSION == _version()


@pytest.mark.parametrize("name", PROMPTS)
def test_editing_any_prompt_changes_the_version(name):
    assert _version(**{name: getattr(config, name) + " "}) != config.PROMPT_VERSION


def test_answer_template_takes_exactly_its_three_placeholders():
    filled = config.ANSWER_TEMPLATE.format(boundary="b", context="c", query="q")
    assert "{" not in filled and "}" not in filled


def test_changing_the_prompts_or_a_model_moves_the_cache_namespace(monkeypatch):
    from src.llm import semantic_cache as sc

    base = sc.cache_namespace("groq")
    assert sc.cache_namespace("groq") == base
    assert sc.cache_namespace("gemini") != base  # different answering model

    monkeypatch.setattr(sc, "PROMPT_VERSION", "edited-prompts")
    assert sc.cache_namespace("groq") != base


def test_eval_fingerprint_changes_when_a_prompt_changes(monkeypatch, tmp_path):
    from eval.harness import store

    chunks = tmp_path / "chunks.json"  # storage/ is not in git, so CI has none
    chunks.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(config, "CHUNKS_PATH", chunks)

    before = store.fingerprint()
    monkeypatch.setattr(config, "ANSWER_TEMPLATE", config.ANSWER_TEMPLATE + " ")
    assert store.fingerprint() != before


def test_every_eval_generation_record_carries_the_prompt_version():
    from eval.harness import generate

    item = {"id": "Q01", "question": "q"}
    out = {"answer": "a", "contexts": ["c"], "outcome": "answer"}
    record = generate.to_record("baseline", item, "fp", "q", out, 10)
    assert record["prompt_version"] == config.PROMPT_VERSION
    assert record["model"]
