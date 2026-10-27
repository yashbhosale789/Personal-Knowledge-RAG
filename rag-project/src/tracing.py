"""
Langfuse tracing for /query (Phase 13.4).

Only a /query request starts a trace (request_trace). The stage hooks — timed() in
src/observability.py and call_llm in src/llm/client.py — add observations only inside
one, so eval runs, scripts and the startup warmup never send anything (Hobby plan:
every observation is a billable unit). The trace ID is the request ID without hyphens:
both are a UUID4's 32 hex digits, so an X-Request-ID opens its trace directly.

Off unless LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set (and
LANGFUSE_TRACING_ENABLED is not "false"). Query, prompt, chunk and answer text is
masked unless TRACING_CAPTURE_CONTENT=true. The SDK exports in a background thread
with LANGFUSE_TIMEOUT (default 5 s), and every hook here swallows its own errors:
tracing must never fail or slow a request.
"""

import logging
import os
import re
import sys
import threading
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from contextvars import ContextVar
from typing import Any

from config import PROMPT_VERSION

logger = logging.getLogger(__name__)

_client: Any = None
_initialised = False
_init_lock = threading.Lock()
# True only inside request_trace(): the hooks below do nothing anywhere else.
_active: ContextVar[bool] = ContextVar("tracing_active", default=False)

# timed() stage -> (observation name, Langfuse observation type).
STAGES = {
    "cache_embed": ("embed-query-for-cache", "embedding"),
    "cache_lookup": ("lookup-semantic-cache", "retriever"),
    "dense_embed": ("embed-query", "embedding"),
    "dense_retrieve": ("search-dense-index", "retriever"),
    "bm25": ("search-bm25-index", "retriever"),
    "fusion": ("fuse-rankings", "span"),
    "rerank": ("rerank-chunks", "span"),
    "cache_store": ("store-in-cache", "span"),
}

# call_llm stage -> generation name.
GENERATIONS = {
    "rewrite": "rewrite-query",
    "sufficiency": "check-context-sufficiency",
    "generate": "generate-answer",
    "citation_verify": "verify-citations",
}

# Identifiers and verdict labels; kept readable when content is masked.
_UNMASKED_KEYS = frozenset(
    {"request_id", "provider", "outcome", "confidence", "tier", "token_source", "hit"}
)
_TRACE_ID = re.compile(r"^[0-9a-f]{32}$")


def capture_content() -> bool:
    return os.getenv("TRACING_CAPTURE_CONTENT", "false").lower() == "true"


def mask(*, data: Any, **_: Any) -> Any:
    """Replaces every string with its length; keeps structure, numbers and _UNMASKED_KEYS."""
    return _mask(data)


def _mask(value: Any, key: str | None = None) -> Any:
    if key in _UNMASKED_KEYS:
        return value
    if isinstance(value, str):
        return f"[masked: {len(value)} chars]"
    if isinstance(value, dict):
        return {k: _mask(v, k) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_mask(v) for v in value]
    return value


def _get_client() -> Any:
    """The Langfuse client, created on first use (after .env is loaded); None when off."""
    global _client, _initialised
    if _initialised:
        return _client
    with _init_lock:
        if not _initialised:
            keys = os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
            off = os.getenv("LANGFUSE_TRACING_ENABLED", "true").lower() == "false"
            if keys and not off:
                try:
                    from langfuse import Langfuse

                    _client = Langfuse(mask=None if capture_content() else mask)
                except Exception:
                    logger.warning(
                        "Langfuse client setup failed; tracing off", exc_info=True
                    )
            _initialised = True
    return _client


class Observation:
    """Wraps a Langfuse observation; a no-op when tracing is off or failed."""

    def __init__(self, obs: Any = None):
        self._obs = obs

    def update(self, **fields: Any) -> None:
        if self._obs is None:
            return
        try:
            self._obs.update(**fields)
        except Exception:
            logger.warning("Langfuse observation update failed", exc_info=True)


_NOOP = Observation()


@contextmanager
def _guarded(make: Callable[[], AbstractContextManager]) -> Iterator[Observation]:
    """Enters make() and yields its observation. Langfuse errors are logged, never raised."""
    cm: AbstractContextManager | None
    try:
        cm = make()
        obs = Observation(cm.__enter__())
    except Exception:
        logger.warning(
            "Langfuse observation failed; continuing untraced", exc_info=True
        )
        cm = None
    if cm is None:
        yield _NOOP
        return
    try:
        yield obs
    except BaseException as e:
        obs.update(level="ERROR", status_message=f"{type(e).__name__}: {e}")
        _exit(cm, sys.exc_info())
        raise
    _exit(cm, (None, None, None))


def _exit(cm: AbstractContextManager, exc_info: tuple) -> None:
    try:
        cm.__exit__(*exc_info)
    except Exception:
        logger.warning("Langfuse observation end failed", exc_info=True)


@contextmanager
def request_trace(request_id: str, query: str) -> Iterator[Observation]:
    """The root of one /query trace. Yields the root observation for its output."""
    client = _get_client()
    if client is None:
        yield _NOOP
        return

    @contextmanager
    def root() -> Iterator[Any]:
        from langfuse import propagate_attributes

        trace_id = request_id.replace("-", "")
        context = {"trace_id": trace_id} if _TRACE_ID.match(trace_id) else None
        with (
            propagate_attributes(
                trace_name="rag-query",
                version=PROMPT_VERSION,
                metadata={"request_id": request_id},
            ),
            client.start_as_current_observation(
                as_type="span",
                name="rag-query",
                trace_context=context,
                input={"query": query},
            ) as span,
        ):
            yield span

    with _guarded(root) as obs:
        token = _active.set(obs is not _NOOP)
        try:
            yield obs
        finally:
            _active.reset(token)


def observe(name: str, as_type: str = "span", **fields: Any) -> AbstractContextManager:
    """A child observation of the current /query trace; a no-op outside one."""
    if not _active.get():
        return nullcontext(_NOOP)
    client = _get_client()
    return _guarded(
        lambda: client.start_as_current_observation(
            as_type=as_type, name=name, **fields
        )
    )


def observe_stage(stage: str) -> AbstractContextManager:
    name, as_type = STAGES.get(stage, (stage, "span"))
    return observe(name, as_type)


def observe_generation(stage: str, **fields: Any) -> AbstractContextManager:
    return observe(GENERATIONS.get(stage, "llm-call"), "generation", **fields)


def shutdown() -> None:
    """Flushes buffered spans at app shutdown (bounded by LANGFUSE_TIMEOUT)."""
    if _client is None:
        return
    try:
        _client.shutdown()
    except Exception:
        logger.warning("Langfuse shutdown failed", exc_info=True)
