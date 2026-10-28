"""Eval-harness math and the deterministic dataset checks. No LLM, no network."""

import json

import pytest

from eval.harness import compare, gate, retrieval_eval, store
from eval.paths import GOLDEN_PATH
from eval.tools import validate_dataset as vd


def _ranked(*pairs):
    return [{"metadata": {"filename": src}, "text": text} for src, text in pairs]


def _item(*spans, any_of=False):
    return {
        "relevant": [{"source": s, "evidence": e} for s, e in spans],
        "any_of": any_of,
    }


# --- retrieval metrics -----------------------------------------------------


def test_chunk_source_uses_the_basename_of_either_path_field():
    assert (
        retrieval_eval.chunk_source({"metadata": {"source": "D:\\x\\a.pdf"}}) == "a.pdf"
    )
    assert (
        retrieval_eval.chunk_source({"metadata": {"filename": "/x/b.pdf"}}) == "b.pdf"
    )


def test_hit_at_rank_one():
    ranked = _ranked(("a.pdf", "Use the lug wrench to tighten"), ("b.pdf", "other"))
    out = retrieval_eval.score(_item(("a.pdf", "lug wrench")), ranked, (1, 5))
    assert out["recall@1"] == out["recall@5"] == 1.0
    assert out["mrr"] == 1.0


def test_hit_at_rank_three_has_reciprocal_rank():
    ranked = _ranked(("a.pdf", "x"), ("a.pdf", "y"), ("a.pdf", "the jacking point"))
    out = retrieval_eval.score(_item(("a.pdf", "jacking point")), ranked, (1, 5))
    assert out["recall@1"] == 0.0
    assert out["recall@5"] == 1.0
    assert out["mrr"] == pytest.approx(1 / 3)


def test_miss_scores_zero():
    out = retrieval_eval.score(
        _item(("a.pdf", "absent")), _ranked(("a.pdf", "x")), (5,)
    )
    assert out == {"recall@5": 0.0, "success@5": 0.0, "mrr": 0.0}


def test_source_must_match_as_well_as_evidence():
    out = retrieval_eval.score(
        _item(("a.pdf", "jacking point")), _ranked(("b.pdf", "the jacking point")), (5,)
    )
    assert out["recall@5"] == 0.0


def test_matching_ignores_case_punctuation_and_whitespace():
    ranked = _ranked(("a.pdf", "Use the Lug-Wrench,\n to tighten"))
    out = retrieval_eval.score(_item(("a.pdf", "lug wrench to")), ranked, (5,))
    assert out["recall@5"] == 1.0


def test_multi_span_recall_is_a_fraction_and_success_needs_all():
    ranked = _ranked(("a.pdf", "first fact"), ("a.pdf", "filler"))
    item = _item(("a.pdf", "first fact"), ("a.pdf", "second fact"))
    out = retrieval_eval.score(item, ranked, (5,))
    assert out["recall@5"] == 0.5
    assert out["success@5"] == 0.0


def test_any_of_needs_only_one_span():
    ranked = _ranked(("a.pdf", "first fact"))
    item = _item(("a.pdf", "first fact"), ("a.pdf", "second fact"), any_of=True)
    out = retrieval_eval.score(item, ranked, (5,))
    assert out["recall@5"] == out["success@5"] == 1.0


# --- paired statistics -----------------------------------------------------


def test_sign_test_known_values():
    assert compare.sign_test(8, 1) == pytest.approx(0.0390625)
    assert compare.sign_test(0, 0) == 1.0
    assert compare.sign_test(5, 5) == 1.0
    assert compare.sign_test(10, 0) == pytest.approx(2 / 1024)


def test_sign_test_is_symmetric_and_bounded():
    assert compare.sign_test(2, 9) == compare.sign_test(9, 2)
    assert 0 <= compare.sign_test(1, 30) <= 1


def test_bootstrap_ci_of_a_constant_is_that_constant():
    assert compare.bootstrap_ci([0.5] * 10, 0.05) == (0.5, 0.5)


def test_bootstrap_ci_is_deterministic_and_brackets_the_mean():
    diffs = [0.2, 0.0, 0.4, 0.1, -0.1, 0.3, 0.2, 0.0]
    low, high = compare.bootstrap_ci(diffs, 0.05)
    assert (low, high) == compare.bootstrap_ci(diffs, 0.05)
    assert low <= sum(diffs) / len(diffs) <= high


def test_wider_confidence_gives_a_wider_interval():
    diffs = [0.2, 0.0, 0.4, 0.1, -0.1, 0.3, 0.2, 0.0]
    narrow = compare.bootstrap_ci(diffs, 0.5)
    wide = compare.bootstrap_ci(diffs, 0.01)
    assert wide[0] <= narrow[0] and wide[1] >= narrow[1]


def test_verdict_no_difference_when_interval_spans_zero():
    out = compare.verdict(
        [0.1, -0.1] * 5, p=0.9, low=-0.2, high=0.2, alpha=0.05, min_effect=0
    )
    assert out.startswith("no evidence")


def test_verdict_names_the_better_side():
    args = {"p": 0.001, "low": 0.5, "high": 1.0, "alpha": 0.05, "min_effect": 0.0}
    assert compare.verdict([1.0] * 10, **args) == "A higher"
    assert compare.verdict([-1.0] * 10, **args) == "B higher"


def test_verdict_flags_significant_but_tiny_effects():
    out = compare.verdict(
        [0.1] * 10, p=0.001, low=0.1, high=0.1, alpha=0.05, min_effect=0.5
    )
    assert "smaller than the minimum useful effect" in out


# --- run fingerprints ------------------------------------------------------


def test_ast_hash_ignores_comments_and_whitespace_but_not_logic():
    assert store.ast_hash("x = 1  # note") == store.ast_hash("x   =   1")
    assert store.ast_hash("x = 1") != store.ast_hash("x = 2")


def test_context_hash_is_order_sensitive():
    assert store.context_hash(["a", "b"]) != store.context_hash(["b", "a"])
    assert store.context_hash(["a", "b"]) == store.context_hash(["a", "b"])


def test_record_key_format():
    assert store.key("ci", "Q01", "abc") == "ci|Q01|abc"


def test_store_round_trips_appended_records(tmp_path):
    path = tmp_path / "runs.jsonl"
    store.append(path, {"key": "k1", "v": 1})
    store.append(path, {"key": "k2", "v": 2})
    assert store.load(path) == {
        "k1": {"key": "k1", "v": 1},
        "k2": {"key": "k2", "v": 2},
    }
    assert store.load(tmp_path / "missing.jsonl") == {}


# --- CI gate ---------------------------------------------------------------

ITEMS = [
    {"id": "A", "expected_outcome": "answer"},
    {"id": "B", "expected_outcome": "abstain"},
]
GENS = {
    "v|A|f": {"key": "v|A|f", "refused": False},
    "v|B|f": {"key": "v|B|f", "refused": True},
}
JUDGED = {
    f"v|A|f|{m}": {"score": s}
    for m, s in (("faithfulness", 1.0), ("relevancy", 0.9), ("correctness", 1.0))
}


def test_gate_passes_a_good_run():
    problems, failures, means = gate.evaluate(ITEMS, GENS, JUDGED, "v", "f", 0.85, 0.75)
    assert (problems, failures) == ([], [])
    assert means["faithfulness"] == 1.0


def test_gate_fails_below_the_floor():
    _, failures, _ = gate.evaluate(ITEMS, GENS, JUDGED, "v", "f", 1.01, 0.75)
    assert any("faithfulness" in f for f in failures)


def test_gate_fails_when_an_answerable_question_is_refused():
    refused = {**GENS, "v|A|f": {"key": "v|A|f", "refused": True}}
    _, failures, _ = gate.evaluate(ITEMS, refused, JUDGED, "v", "f", 0.85, 0.75)
    assert any("expected an answer" in f for f in failures)


def test_gate_fails_when_an_unanswerable_question_is_answered():
    answered = {**GENS, "v|B|f": {"key": "v|B|f", "refused": False}}
    _, failures, _ = gate.evaluate(ITEMS, answered, JUDGED, "v", "f", 0.85, 0.75)
    assert any("expected a refusal" in f for f in failures)


def test_gate_reports_missing_generations_as_problems_not_failures():
    problems, _, _ = gate.evaluate(ITEMS, {}, JUDGED, "v", "f", 0.85, 0.75)
    assert len(problems) == 2


# --- dataset validator -----------------------------------------------------

CHUNKS = {
    "a.pdf": [
        vd.norm("Position the jack under the jacking point nearest the flat tyre.")
    ]
}


def test_norm_collapses_unicode_case_and_punctuation():
    assert vd.norm("A ventro compart-\nment Tra\ufb03c") == "aventrocompartmenttraffic"
    assert vd.norm("It\u2019s") == vd.norm("It's") == "its"


def test_basename_handles_both_separators():
    assert vd.basename("D:\\a\\b c.pdf") == vd.basename("/a/b c.pdf") == "b c.pdf"


def test_check_span_accepts_a_real_span():
    rel = {"source": "a.pdf", "evidence": "jack under the jacking point nearest"}
    assert vd.check_span(rel, CHUNKS)[0] == []


def test_check_span_rejects_unknown_source_and_missing_evidence():
    assert vd.check_span({"source": "zzz.pdf", "evidence": "x"}, CHUNKS)[0]
    assert vd.check_span({"source": "a.pdf", "evidence": "not in any chunk"}, CHUNKS)[0]
    assert vd.check_span({"source": "a.pdf", "evidence": ""}, CHUNKS)[0] == [
        "empty evidence"
    ]


def _valid_item(**over):
    base = {
        "id": "Q1",
        "question": "q?",
        "ground_truth": "gt",
        "ci": False,
        "category": "normal",
        "difficulty": "easy",
        "expected_outcome": "answer",
        "origin": "manual",
        "split": "dev",
        "relevant": [
            {"source": "a.pdf", "evidence": "jack under the jacking point nearest"}
        ],
    }
    base.update(over)
    return base


def test_valid_item_has_no_errors():
    missing = vd.REQUIRED - _valid_item().keys()
    errors, _ = vd.check_item(_valid_item(), CHUNKS, set())
    assert not missing
    assert errors == []


def test_duplicate_ids_are_errors():
    seen: set[str] = set()
    vd.check_item(_valid_item(), CHUNKS, seen)
    errors, _ = vd.check_item(_valid_item(), CHUNKS, seen)
    assert any("duplicate id" in e for e in errors)


def test_abstain_items_must_have_no_spans():
    errors, _ = vd.check_item(_valid_item(expected_outcome="abstain"), CHUNKS, set())
    assert any("abstain items must have relevant=[]" in e for e in errors)


def test_answer_items_need_a_span():
    errors, _ = vd.check_item(_valid_item(relevant=[]), CHUNKS, set())
    assert any("at least one relevant span" in e for e in errors)


def test_golden_dataset_structure():
    """Structure-only checks that need no chunks.json (span checks run in CI after ingest)."""
    dataset = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    ids = [i["id"] for i in dataset]
    assert len(ids) == len(set(ids))
    assert all(vd.REQUIRED <= i.keys() for i in dataset)
    for item in dataset:
        assert (item["expected_outcome"] == "abstain") == (not item["relevant"])
    assert any(i["ci"] and i["expected_outcome"] == "abstain" for i in dataset)
    assert {i["split"] for i in dataset} <= {"dev", "test"}


# --- token accounting (Phase 13.3) -----------------------------------------


def test_eval_summary_reports_tokens_per_query_and_estimates():
    from eval.harness.generate import token_summary

    def call(stage, p, c, source="reported"):
        return {
            "stage": stage,
            "prompt_tokens": p,
            "completion_tokens": c,
            "prompt_source": source,
            "completion_source": "reported",
        }

    usages = [
        {
            "calls": [call("sufficiency", 300, 20), call("generate", 900, 80)],
            "prompt_tokens": 1200,
            "completion_tokens": 100,
            "estimated": False,
        },
        {
            "calls": [call("sufficiency", 280, 20, source="estimated")],
            "prompt_tokens": 280,
            "completion_tokens": 20,
            "estimated": True,
        },
    ]
    line = token_summary(usages)
    assert "mean=800 p50=1300 max=1300" in line
    assert "generate=490 sufficiency=310" in line
    assert "1/2 include estimates" in line


def test_run_ids_ignore_formatting_but_track_content(tmp_path):
    golden, chunks = tmp_path / "g.json", tmp_path / "c.json"
    golden.write_text('[{"id": "Q01", "q": "a"}]', encoding="utf-8")
    chunks.write_text('[{"text": "x"}]', encoding="utf-8")
    ids = store.run_ids(golden, chunks)
    assert set(ids) == {"dataset", "corpus"} and all(len(v) == 10 for v in ids.values())

    golden.write_bytes(
        b'[\r\n  {"q": "a",\r\n   "id": "Q01"}\r\n]'
    )  # CRLF, reordered keys
    assert store.run_ids(golden, chunks) == ids

    golden.write_text('[{"id": "Q01", "q": "b"}]', encoding="utf-8")
    assert store.run_ids(golden, chunks)["dataset"] != ids["dataset"]
