"""
Thin wrapper around the OpenAI API used by every stage of the drafting
pipeline (outline, draft, critique, style pass, topic scoring).

Function names are kept as call_claude / call_claude_with_web_search so
nothing else in the pipeline needs to change if you swap providers again
later -- only this file and config/settings.yaml's `model` value need to
be touched.
"""
from __future__ import annotations

import os
from functools import lru_cache

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.settings import get_settings


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and fill it in, "
            "or export it in your shell / GitHub Actions secrets."
        )
    return OpenAI(api_key=api_key)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=20))
def call_claude(
    system: str,
    user: str,
    max_tokens: int | None = None,
    tools: list[dict] | None = None,
) -> str:
    """
    Single-turn OpenAI call via the Responses API. Returns the concatenated
    output text. Retries on transient API errors with exponential backoff.
    """
    settings = get_settings()
    kwargs = dict(
        model=settings["model"],
        instructions=system,
        input=user,
        max_output_tokens=max_tokens or settings["max_tokens_per_call"],
    )
    if tools:
        kwargs["tools"] = tools

    response = _client().responses.create(**kwargs)
    return response.output_text.strip()


def call_claude_with_web_search(system: str, user: str, max_tokens: int | None = None) -> str:
    """
    Same as call_claude but enables OpenAI's hosted web search tool, for
    stages that need to fact-ground claims (drafting, critique).

    Uses {"type": "web_search"} -- the current recommended tool type for new
    Responses API integrations. The older "web_search_preview" type still
    works but lacks newer controls (domain filters, live-access toggle) and
    is intended for legacy integrations only.
    """
    return call_claude(
        system=system,
        user=user,
        max_tokens=max_tokens,
        tools=[{"type": "web_search"}],
    )
