"""LLM integration service supporting OpenRouter and OpenAI-compatible providers."""

import logging
import re
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from backend.app.config import (
    FRONTEND_URL,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
)

logger = logging.getLogger("weather_advisory.llm")


def sanitize_llm_error(error: Exception) -> str:
    """Sanitizes an exception message to guarantee no API keys or tokens are leaked into logs."""
    msg = str(error)
    # Strip potential Bearer tokens or sk-or-... tokens
    msg = re.sub(r"Bearer\s+[\w\.\-]+", "Bearer [REDACTED]", msg)
    msg = re.sub(r"sk-[a-zA-Z0-9\-_]{8,}", "sk-[REDACTED]", msg)
    return f"{error.__class__.__name__}: {msg}"


class QueryUnderstandingResult(BaseModel):
    """Structured extraction of user intent and context from their query."""

    activity: Optional[str] = Field(
        default=None,
        description=(
            "The outdoor activity mentioned (e.g., 'cycling', 'running', 'picnic', 'walking'). "
            "If continuing a conversation and the activity is unchanged, retain the prior activity."
        ),
    )
    location: Optional[str] = Field(
        default=None,
        description=(
            "The target city or geographic locality name (e.g., 'Bangalore', 'Delhi', 'Tokyo'). "
            "If continuing a conversation and the location is unchanged, retain the prior location. "
            "Do NOT fabricate or invent a location if none is mentioned."
        ),
    )
    time_context: Optional[str] = Field(
        default=None,
        description=(
            "Temporal context mentioned (e.g., 'today', 'this evening', 'tomorrow morning', 'now')."
        ),
    )
    person_context: Optional[str] = Field(
        default=None,
        description=(
            "Any mention of participants or vulnerability (e.g., 'child', 'elderly', 'solo', 'asthma')."
        ),
    )


def is_llm_configured() -> bool:
    """Check if LLM API credentials are configured."""
    return bool(LLM_API_KEY and LLM_API_KEY.strip())


def validate_llm_configuration() -> bool:
    """Validates LLM configuration at startup and displays clear user guidance.

    Returns True if LLM_API_KEY is configured, False otherwise.
    NEVER logs or exposes the actual key value.
    """
    if not is_llm_configured():
        logger.warning(
            "LLM_API_KEY is not configured. Please add your OpenRouter API key to .env. "
            "The application will operate using deterministic factual responses."
        )
        return False

    logger.info(
        f"OpenRouter LLM configured: model='{LLM_MODEL}', base_url='{LLM_BASE_URL}' (API key: [CONFIGURED])"
    )
    return True


def get_chat_model(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.0,
) -> Optional[ChatOpenAI]:
    """Instantiate and return a ChatOpenAI model configured for OpenRouter / OpenAI-compatible endpoint.

    Returns None if no API key is provided.
    """
    key = api_key or LLM_API_KEY
    if not key or not key.strip():
        return None

    clean_key = key.strip().strip('"').strip("'")
    target_model = model or LLM_MODEL or "openrouter/free"
    target_base = base_url or LLM_BASE_URL or "https://openrouter.ai/api/v1"

    kwargs: dict[str, Any] = {
        "model": target_model,
        "api_key": clean_key,
        "base_url": target_base,
        "temperature": temperature,
        "default_headers": {
            "HTTP-Referer": FRONTEND_URL or "http://localhost:3000",
            "X-Title": "Weather Advisory Support Bot",
        },
    }

    return ChatOpenAI(**kwargs)
