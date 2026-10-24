import pytest

import config
from src.retrieval.fusion import reciprocal_rank_fusion


def _d(text):
    return {"text": text, "metadata": {}}


def test_document_in_both_lists_beats_single_list_documents():
    dense = [_d("a"), _d("b")]
    sparse = [_d("c"), _d("b")]
    fused = reciprocal_rank_fusion([dense, sparse])
    assert fused[0]["text"] == "b"


def test_rrf_score_formula():
    fused = reciprocal_rank_fusion([[_d("a")], [_d("b"), _d("a")]])
    by_text = {d["text"]: d for d in fused}
    assert by_text["a"]["rrf_scores"] == pytest.approx(
        1 / config.RRF_K + 1 / (config.RRF_K + 1)
    )
    assert by_text["b"]["rrf_scores"] == pytest.approx(1 / config.RRF_K)


def test_duplicates_are_collapsed_and_ranked():
    fused = reciprocal_rank_fusion([[_d("a"), _d("b")], [_d("a")]])
    assert [d["text"] for d in fused] == ["a", "b"]
    assert [d["rrf_rank"] for d in fused] == [0, 1]


def test_top_k_truncates():
    fused = reciprocal_rank_fusion([[_d(str(i)) for i in range(10)]], top_k=3)
    assert len(fused) == 3


def test_original_fields_are_preserved_and_input_not_mutated():
    original = {"text": "a", "metadata": {"filename": "x.pdf"}, "score": 1.5}
    fused = reciprocal_rank_fusion([[original]])
    assert fused[0]["metadata"] == {"filename": "x.pdf"}
    assert "rrf_rank" not in original


def test_empty_lists_give_empty_result():
    assert reciprocal_rank_fusion([[], []]) == []
