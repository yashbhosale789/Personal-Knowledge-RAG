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

if PIPELINE_PROVIDER not in _PROVIDERS:
    raise ValueError(
        f"Unknown PIPELINE_PROVIDER '{PIPELINE_PROVIDER}'. "
        "Choose: openrouter | groq | gemini | ollama"
    )

ACTIVE_MODEL, ACTIVE_URL, ACTIVE_KEY_ENV = _PROVIDERS[PIPELINE_PROVIDER]
logger.info(f"Pipeline LLM: {PIPELINE_PROVIDER} — {ACTIVE_MODEL}")


def _call_openai_compatible(messages: list) -> str:
    """OpenRouter, Groq, Gemini — all speak the same OpenAI-compatible shape."""
    payload = {
        "model": ACTIVE_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 512,
    }
    headers = {"Content-Type": "application/json"}
    if ACTIVE_KEY_ENV:
        headers["Authorization"] = f"Bearer {os.getenv(ACTIVE_KEY_ENV)}"
        headers["HTTP-Referer"] = "https://github.com/personal-kb-rag"

    response = requests.post(ACTIVE_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def _call_ollama(messages: list) -> str:
    """
    Ollama native /api/chat — NOT /v1/chat/completions.
    The OpenAI-compatible route silently ignores options.num_ctx and defaults
    to the model's max context, causing a 13GB+ KV-cache OOM on 4GB VRAM.
    Native /api/chat respects num_ctx correctly.
    """
    payload = {
        "model": ACTIVE_MODEL,
        "messages": messages,
        "options": {"num_ctx": 2048},
        "stream": False,
    }
    # Local inference is slower than hosted APIs, especially cold start
    # when the model has to load into VRAM.
    response = requests.post(ACTIVE_URL, json=payload, timeout=300)
    response.raise_for_status()
    return response.json()["message"]["content"].strip()


def call_llm(prompt: str, system: str = "") -> str:
    """
    Send a prompt to the active pipeline LLM and return the response text.
    Provider is controlled by PIPELINE_PROVIDER in config.py.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        if PIPELINE_PROVIDER == "ollama":
            return _call_ollama(messages)
        return _call_openai_compatible(messages)

    except requests.exceptions.Timeout:
        logger.error(f"{PIPELINE_PROVIDER} request timeout")
        raise

    except requests.exceptions.HTTPError as e:
        logger.error(
            f"{PIPELINE_PROVIDER} HTTP error: {e.response.status_code} — {e.response.text}"
        )
        raise

    except KeyError as e:
        logger.error(f"{PIPELINE_PROVIDER} unexpected response format: {e}")
        raise
