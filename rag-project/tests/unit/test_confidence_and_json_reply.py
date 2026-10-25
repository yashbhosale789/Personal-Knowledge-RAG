import json

import pytest

from src.pipeline.confidence import CAVEAT_TEXT, score_confidence
from src.pipeline.json_reply import parse_json_reply


def test_grounded_answer_is_high_confidence_without_caveat():
    assert score_confidence({"grounded": True}) == {
        "confidence": "high",
        "caveat": None,
    }


def test_ungrounded_answer_is_low_confidence_with_caveat():
    assert score_confidence({"grounded": False}) == {
        "confidence": "low",
        "caveat": CAVEAT_TEXT,
    }


def test_parses_bare_json():
    assert parse_json_reply('{"grounded": true}') == {"grounded": True}


def test_parses_fenced_json():
    assert parse_json_reply('```json\n{"grounded": false}\n```') == {"grounded": False}


def test_parses_json_embedded_in_prose():
    assert parse_json_reply('Sure: {"a": 1} done') == {"a": 1}


def test_multiline_object():
    assert parse_json_reply('{\n "a": 1,\n "b": [1, 2]\n}') == {"a": 1, "b": [1, 2]}


def test_reply_without_object_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_json_reply("no json here")


def test_malformed_object_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_json_reply("{not json}")
