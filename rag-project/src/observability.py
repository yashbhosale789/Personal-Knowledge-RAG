"""
Request correlation and non-LLM stage timing for /query (Phase 13.4 steps 1-2).

request_id is set by the API middleware. RequestIdFilter copies it onto every log
record, so loggers in api/ and src/ carry it without passing it around. A worker
thread only sees it when started with the caller's context (run_in_threadpool,
asyncio.to_thread); a bare loop.run_in_executor does not copy it.

timed(stage) records a stage's self-time: time spent in a nested timed() block is
subtracted from its parent, so recorded stages never overlap and can be summed.
LLM calls are timed by src/llm/usage.py, not here. Inside a /query trace each timed()
stage is also a Langfuse observation (src/tracing.py).
"""

import json
import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from prometheus_client import Histogram

from src import tracing

STAGE_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)

stage_duration_seconds = Histogram(
    "rag_stage_duration_seconds",
    "Self-time of a non-LLM /query stage (nested stages excluded).",
    ["stage"],
    buckets=STAGE_LATENCY_BUCKETS,
)

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_stages: ContextVar[list[dict] | None] = ContextVar("stages", default=None)
# Seconds spent in child stages of the innermost open timed() block.
_children: ContextVar[list[float] | None] = ContextVar("stage_children", default=None)


class RequestIdFilter(logging.Filter):
    """Adds record.request_id unless the call already passed one via extra=."""

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "request_id", None) is None:
            record.request_id = request_id.get()
        return True


class JsonFormatter(logging.Formatter):
    """
    One JSON object per line. A message that is already a JSON object (the event
    logs) gets request_id merged in; any other message is wrapped.
    """

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        payload = None
        if message.startswith("{"):
            try:
                payload = json.loads(message)
            except ValueError:
                pass
        if not isinstance(payload, dict):
            payload = {
                "level": record.levelname,
                "logger": record.name,
                "message": message,
            }
            if record.exc_info:
                payload["exc_info"] = self.formatException(record.exc_info)
        payload.setdefault("request_id", getattr(record, "request_id", None))
        return json.dumps(payload)


@contextmanager
def timed(stage: str) -> Iterator[tracing.Observation]:
    """Also a Langfuse observation inside a /query trace; yields it for input/output."""
    children = [0.0]
    token = _children.set(children)
    start = time.perf_counter()
    try:
        with tracing.observe_stage(stage) as observation:
            yield observation
    finally:
        elapsed = time.perf_counter() - start
        _children.reset(token)
        parent = _children.get()
        if parent is not None:
            parent[0] += elapsed
        seconds = elapsed - children[0]
        stage_duration_seconds.labels(stage).observe(seconds)
        stages = _stages.get()
        if stages is not None:
            stages.append({"stage": stage, "ms": seconds * 1000})


@contextmanager
def track() -> Iterator[list[dict]]:
    """Collects every timed() stage run inside the block, threads included."""
    stages: list[dict] = []
    token = _stages.set(stages)
    try:
        yield stages
    finally:
        _stages.reset(token)


def summarize(stages: list[dict]) -> dict[str, float]:
    """Milliseconds per stage, summed over repeats (e.g. retried pipeline attempts)."""
    totals: dict[str, float] = {}
    for s in stages:
        totals[s["stage"]] = totals.get(s["stage"], 0.0) + s["ms"]
    return {stage: round(ms, 1) for stage, ms in totals.items()}
