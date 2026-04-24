"""
LLM wrapper — supports Anthropic Claude OR OpenAI GPT.

Switch providers by setting LLM_PROVIDER=anthropic or LLM_PROVIDER=openai in .env.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.content.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_anthropic_client = None
_openai_client = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set in .env")
        _anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in .env")
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def _ask_anthropic(messages: list[dict], max_tokens: int, temperature: float) -> str:
    client = _get_anthropic_client()
    resp = await client.messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "\n".join(parts).strip() or "..."


async def _ask_openai(messages: list[dict], max_tokens: int, temperature: float) -> str:
    client = _get_openai_client()
    # OpenAI takes system prompt as the first message, not a separate param
    openai_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=openai_messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip() or "..."


async def ask_claude(
    messages: list[dict],
    *,
    max_tokens: int = 600,
    temperature: float = 0.4,
) -> str:
    """
    Send a conversation to the configured LLM and return the text reply.

    `messages` must be a list of {"role": "user"|"assistant", "content": str}.
    The function is still named ask_claude for backwards compatibility with
    the routers, but it routes based on settings.llm_provider.
    """
    provider = settings.llm_provider.lower()
    try:
        if provider == "openai":
            return await _ask_openai(messages, max_tokens, temperature)
        return await _ask_anthropic(messages, max_tokens, temperature)
    except Exception as exc:
        logger.exception("LLM API error (provider=%s): %s", provider, exc)
        return (
            "Serivisi yacu ntiri gukora muri iki gihe. Turimo gukemura ikibazo, iragaruka vuba. "
            "Sorry, I'm having trouble right now. Please try again in a moment."
        )
