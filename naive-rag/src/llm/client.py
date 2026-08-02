import requests
import os
import logging
from dotenv import load_dotenv
from config import OPENROUTER_API_URL, OPENROUTER_MODEL

from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

# load_dotenv()

logger = logging.getLogger(__name__)

# OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# OPENROUTER_MODEL = "meta-llama/llama-3.1-8b-instruct:free"

def get_api_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY")
    # print(f"DEBUG — key loaded: '{key}'")
    if not key:
        raise EnvironmentError(
            "OPENROUTER_API_KEY not found. "
            "Create a .env file with: OPENROUTER_API_KEY=your_key_here"
        )
    return key

def call_llm(prompt : str, system: str = "") -> str:
    """
    Send a prompt to OpenRouter and return the response text.

    Args:
        prompt: The user message (will contain retrieved context + query)
        system: Optional system instruction to set model behaviour

    Returns:
        The model's response as a plain string
    """

    messages = []

    if system:
        messages.append({"role": "system", "content" : system})

    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.2,  # low = more deterministic, better for factual QA
        "max_tokens": 512,
    }

    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/personal-kb-rag",  # OpenRouter asks for this
    }

    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    except requests.exceptions.Timeout:
        logger.error("OpenRouter request timeout")
        raise

    except requests.exceptions.HTTPError as e:
        logger.error(
            f"OpenRouter HTTP error: {e.response.status_code} — {e.response.text}"
        )
        raise

    except KeyError:
        logger.error(f"Unexpected response format : {data}")
        raise
