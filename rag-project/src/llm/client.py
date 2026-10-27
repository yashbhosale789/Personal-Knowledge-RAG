import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent)

from config import (
    GEMINI_API_KEY,
    GEMINI_API_URL,
    GEMINI_PIPELINE_MODEL,
    GROQ_API_KEY,
    GROQ_API_URL,
    GROQ_PIPELINE_MODEL,
    OLLAMA_API_URL,
    OLLAMA_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_API_URL,
    OPENROUTER_MODEL,
    PIPELINE_PROVIDER,
)
from src import tracing
from src.llm import usage

logger = logging.getLogger(__name__)

_PROVIDERS = {
    "openrouter": (OPENROUTER_MODEL, OPENROUTER_API_URL, OPENROUTER_API_KEY),
    "groq": (GROQ_PIPELINE_MODEL, GROQ_API_URL, GROQ_API_KEY),
    "gemini": (GEMINI_PIPELINE_MODEL, GEMINI_API_URL, GEMINI_API_KEY),
    "ollama": (OLLAMA_MODEL, OLLAMA_API_URL, None),  # no API key needed
}

if PIPELINE_PROVIDER not in _PROVIDERS:
    raise ValueError(
        f"Unknown PIPELINE_PROVIDER '{PIPELINE_PROVIDER}'. "
        "Choose: openrouter | groq | gemini | ollama"
    )

logger.info(f"Pipeline LLM configured: {PIPELINE_PROVIDER}")

# One pooled session for every provider: a /query makes up to four sequential LLM
# calls, and reusing the connection skips a TCP + TLS handshake on each of them.
_session = requests.Session()


def _resolve_provider(provider: str | None) -> tuple[str, str, str, str | None]:
    """
    Resolve (provider_name, model, url, key_env) for this call.
    Reads config.PIPELINE_PROVIDER fresh, at call time — not at import time —
    so runtime provider switches (e.g. from api/routers/query.py) actually take effect.
    """
    import config

    active = provider or config.PIPELINE_PROVIDER

    if active not in _PROVIDERS:
        raise ValueError(
            f"Unknown provider '{active}'. Choose: openrouter | groq | gemini | ollama"
        )

    model, url, key_env = _PROVIDERS[active]
    return active, model, url, key_env


def model_name(provider: str | None = None) -> str:
    """The model a call_llm(..., provider=provider) would use."""
    return _resolve_provider(provider)[1]


def _call_openai_compatible(
    messages: list, model: str, url: str, key_env: str | None
) -> tuple[str, dict]:
    """OpenRouter, Groq, Gemini — all speak the same OpenAI-compatible shape."""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 512,
    }
    headers = {"Content-Type": "application/json"}
    if key_env:
        key = os.getenv(key_env)
        if not key:
            raise ValueError(f"{key_env} is not set - cannot call the provider.")

        headers["Authorization"] = f"Bearer {os.getenv(key_env)}"
        headers["HTTP-Referer"] = "https://github.com/personal-kb-rag"

    response = _session.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    response_json = response.json()
    try:
        text = response_json["choices"][0]["message"]["content"].strip()
    except KeyError:
        logger.error(f"{url} returned unexpected shape: {response_json}")
        raise
    return text, response_json.get("usage") or {}


def _call_ollama(messages: list, model, url) -> tuple[str, dict]:
    """
    Ollama native /api/chat — NOT /v1/chat/completions.
    The OpenAI-compatible route silently ignores options.num_ctx and defaults
    to the model's max context, causing a 13GB+ KV-cache OOM on 4GB VRAM.
    Native /api/chat respects num_ctx correctly.
    """
    payload = {
        "model": model,
        "messages": messages,
        "options": {"num_ctx": 2048},
        "stream": False,
    }
    # Local inference is slower than hosted APIs, especially cold start
    # when the model has to load into VRAM.
    response = _session.post(url, json=payload, timeout=300)
    response.raise_for_status()
    body = response.json()
    # Ollama omits prompt_eval_count when the whole prompt was served from its KV cache.
    reported = {
        "prompt_tokens": body.get("prompt_eval_count"),
        "completion_tokens": body.get("eval_count"),
    }
    return body["message"]["content"].strip(), reported


def call_llm(
    prompt: str, system: str = "", provider: str | None = None, stage: str = "other"
) -> str:
    """
    Send a prompt to the active pipeline LLM and return the response text.
    Provider is controlled by PIPELINE_PROVIDER in config.py. `stage` labels the
    token and latency metrics (rewrite | sufficiency | generate | citation_verify).
    """
    active, model, url, key_env = _resolve_provider(provider)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    started = time.monotonic()
    # A Langfuse generation inside a /query trace; a failed call ends it as an ERROR.
    with tracing.observe_generation(
        stage, model=model, input=messages, metadata={"provider": active}
    ) as generation:
        try:
            if active == "ollama":
                text, reported = _call_ollama(messages, model, url)
            else:
                text, reported = _call_openai_compatible(messages, model, url, key_env)

        except requests.exceptions.Timeout:
            logger.error(f"{active} request timeout")
            raise

        except requests.exceptions.HTTPError as e:
            logger.error(
                f"{active} HTTP error: {e.response.status_code} — {e.response.text}"
            )
            raise

        except KeyError as e:
            logger.error(f"{active} unexpected response format: {e}")
            raise

        call = usage.record(
            stage,
            active,
            model,
            time.monotonic() - started,
            reported,
            system + prompt,
            text,
        )
        generation.update(
            output=text,
            usage_details={
                "input": call["prompt_tokens"],
                "output": call["completion_tokens"],
            },
            metadata={
                "provider": active,
                "token_source": "estimated"
                if "estimated" in (call["prompt_source"], call["completion_source"])
                else "reported",
            },
        )
    return text
