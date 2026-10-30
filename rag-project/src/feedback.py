"""
Human feedback (Phase 14.0).

Grounding: what /query served, saved in Redis under its request ID for 24 h, so
POST /feedback stores the server's record of the answer and never the client's.
Records: one SQLite row per request ID, on the feedback_data volume in prod. It is
independent of the index, so re-indexing never touches it.
"""

import json
import logging
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta

import redis

import config
from src.llm.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Plain columns and one JSON field, so a move to Postgres (Phase 15.0) is a copy.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    request_id     TEXT PRIMARY KEY,
    rating         TEXT NOT NULL CHECK (rating IN ('up', 'down')),
    comment        TEXT,
    query          TEXT,
    answer         TEXT,
    outcome        TEXT,
    prompt_version TEXT NOT NULL,
    model          TEXT NOT NULL,
    chunks         TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
)
"""


def save_grounding(request_id: str, grounding: dict) -> None:
    try:
        get_redis_client().set(
            config.FEEDBACK_GROUNDING_PREFIX + request_id,
            json.dumps(grounding),
            ex=config.FEEDBACK_GROUNDING_TTL_SECONDS,
        )
    except redis.RedisError:
        logger.warning("Redis unavailable — feedback grounding not saved")


def load_grounding(request_id: str) -> dict | None:
    """None when unknown or expired. Raises redis.RedisError when Redis is down."""
    raw = get_redis_client().get(config.FEEDBACK_GROUNDING_PREFIX + request_id)
    return json.loads(raw) if raw else None


def _now(now: datetime | None) -> str:
    # One fixed format, so created_at compares correctly as text.
    return (now or datetime.now(UTC)).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    config.FEEDBACK_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.FEEDBACK_DB_PATH, timeout=5)
    conn.execute(_SCHEMA)
    return conn


def record(
    request_id: str,
    rating: str,
    comment: str | None,
    grounding: dict,
    now: datetime | None = None,
) -> None:
    """One row per request ID: a later submission replaces the rating and comment."""
    ts = _now(now)
    with closing(_connect()) as conn, conn:
        conn.execute(
            """
            INSERT INTO feedback (request_id, rating, comment, query, answer, outcome,
                                  prompt_version, model, chunks, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(request_id) DO UPDATE SET
                rating = excluded.rating,
                comment = excluded.comment,
                updated_at = excluded.updated_at
            """,
            (
                request_id,
                rating,
                comment,
                grounding.get("query"),
                grounding.get("answer"),
                grounding.get("outcome"),
                grounding.get("prompt_version") or "unknown",
                grounding.get("model") or "unknown",
                json.dumps(grounding.get("chunks") or []),
                ts,
                ts,
            ),
        )
    purge(now)


def purge(now: datetime | None = None) -> int:
    """Deletes query, answer and comment text past retention; keeps rating, model and sources."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=config.FEEDBACK_RETENTION_DAYS)
    with closing(_connect()) as conn, conn:
        return conn.execute(
            """
            UPDATE feedback SET query = NULL, answer = NULL, comment = NULL
            WHERE created_at < ?
              AND (query IS NOT NULL OR answer IS NOT NULL OR comment IS NOT NULL)
            """,
            (_now(cutoff),),
        ).rowcount
