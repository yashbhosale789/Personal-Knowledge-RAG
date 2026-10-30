import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

import config
from src import feedback

GROUNDING = {
    "query": "How do I change a tyre?",
    "answer": "Loosen the nuts [SOURCE 1].",
    "outcome": "answer",
    "prompt_version": "pv1",
    "model": "m1",
    "chunks": [
        {"n": 1, "source": "tyre.pdf", "page": "3", "snippet": "Loosen", "cited": True}
    ],
}
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "feedback" / "feedback.db"
    monkeypatch.setattr(config, "FEEDBACK_DB_PATH", path)
    return path


def row(db, request_id) -> dict:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        return dict(
            conn.execute(
                "SELECT * FROM feedback WHERE request_id = ?", (request_id,)
            ).fetchone()
        )
    finally:
        conn.close()


def test_purge_drops_text_after_retention_and_keeps_the_rest(db):
    old = NOW - timedelta(days=config.FEEDBACK_RETENTION_DAYS + 1)
    recent = NOW - timedelta(days=config.FEEDBACK_RETENTION_DAYS - 1)
    feedback.record("old", "down", "bad answer", GROUNDING, now=old)
    feedback.record("recent", "up", "fine", GROUNDING, now=recent)

    assert feedback.purge(now=NOW) == 1
    assert feedback.purge(now=NOW) == 0  # idempotent

    purged = row(db, "old")
    assert (purged["query"], purged["answer"], purged["comment"]) == (None, None, None)
    assert purged["rating"] == "down"
    assert (purged["prompt_version"], purged["model"], purged["outcome"]) == (
        "pv1",
        "m1",
        "answer",
    )
    assert json.loads(purged["chunks"]) == GROUNDING["chunks"]

    kept = row(db, "recent")
    assert (kept["query"], kept["comment"]) == (GROUNDING["query"], "fine")


def test_record_purges_as_it_writes(db):
    feedback.record("old", "up", "c", GROUNDING, now=NOW - timedelta(days=200))
    feedback.record("new", "up", None, GROUNDING, now=NOW)
    assert row(db, "old")["query"] is None


def test_records_survive_reopening_the_file(db):
    feedback.record("r1", "up", None, GROUNDING, now=NOW)
    # Each call opens its own connection; a fresh one on the same file still sees the row.
    assert row(db, "r1")["rating"] == "up"
    feedback.record("r1", "down", "changed", GROUNDING, now=NOW)
    assert row(db, "r1")["rating"] == "down"


def test_prod_compose_keeps_the_store_on_a_named_volume():
    """CI's part of 'survives container recreation'; the prod deploy check is the rest."""
    compose = yaml.safe_load(
        (Path(config.BASE_DIR) / "docker-compose.prod.yml").read_text(encoding="utf-8")
    )
    mounts = dict(v.split(":", 1)[::-1] for v in compose["services"]["app"]["volumes"])
    # The image's WORKDIR is /app, so the default path lands on the mount.
    assert config.FEEDBACK_DB_PATH.parent == config.BASE_DIR / "feedback"
    assert mounts["/app/feedback"] in compose["volumes"]
