import requests
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

from config import (
    PIPELINE_PROVIDER,
    OPENROUTER_API_URL,
    OPENROUTER_MODEL,
    OPENROUTER_API_KEY,
    GROQ_API_URL,
    GROQ_PIPELINE_MODEL,
    GROQ_API_KEY,
    GEMINI_API_URL,
    GEMINI_PIPELINE_MODEL,
    GEMINI_API_KEY,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_API_URL,
)

logger = logging.getLogger(__name__)

_PROVIDERS = {
    "openrouter": (OPENROUTER_MODEL, OPENROUTER_API_URL, OPENROUTER_API_KEY),
    "groq": (GROQ_PIPELINE_MODEL, GROQ_API_URL, GROQ_API_KEY),
    "gemini": (GEMINI_PIPELINE_MODEL, GEMINI_API_URL, GEMINI_API_KEY),
    "ollama": (OLLAMA_MODEL, OLLAMA_API_URL, None),  # no API key needed
}


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

def _call_openai_compatible(messages: list, model: str, url:str, key_env: str | None) -> str:
    """OpenRouter, Groq, Gemini — all speak the same OpenAI-compatible shape."""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 512,
    }
    headers = {"Content-Type": "application/json"}
    if key_env:
        headers["Authorization"] = f"Bearer {os.getenv(key_env)}"
        headers["HTTP-Referer"] = "https://github.com/personal-kb-rag"

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def _call_ollama(messages: list, model, url, key_env) -> str:
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
    response = requests.post(url, json=payload, timeout=300)
    response.raise_for_status()
    return response.json()["message"]["content"].strip()


def call_llm(prompt: str, system: str = "", provider: str | None = None) -> str:
    """
    Send a prompt to the active pipeline LLM and return the response text.
    Provider is controlled by PIPELINE_PROVIDER in config.py.
    """
    active, model, url, key_env = _resolve_provider(provider)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        if active == "ollama":
            return _call_ollama(messages, model, url)
        return _call_openai_compatible(messages, model, url, key_env)

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
