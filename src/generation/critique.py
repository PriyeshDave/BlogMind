from __future__ import annotations

import json

from src.utils.claude_client import call_claude
from src.utils.settings import get_settings

CRITIQUE_SYSTEM = """You are a skeptical senior technical editor reviewing a
draft blog post before publication. You are looking for exactly these failure
modes, common in AI-generated technical writing:

1. Vague claims with no concrete backing ("agents are becoming increasingly
   important" — says nothing)
2. Code that looks plausible but wouldn't actually run
3. Numbers or benchmarks stated without a clear source or methodology
4. Generic "AI-sounding" filler sentences that could appear in any post
5. A structure that doesn't deliver on the title's promise
6. Padding to hit a word count instead of being appropriately concise

Respond ONLY with valid JSON, no markdown fences:
{
  "passes_quality_bar": true/false,
  "issues": ["specific issue 1", "specific issue 2"],
  "revision_instructions": "concrete instructions for fixing the issues, or empty string if it passes"
}
"""


def critique_draft(draft_markdown: str) -> dict:
    settings = get_settings()
    user_prompt = f"""Quality bar for this blog:
- Word count between {settings['min_word_count']} and {settings['max_word_count']}
- Must contain a code block: {settings['require_code_block']}
- Must contain a concrete number or dataset: {settings['require_concrete_number_or_data']}

Draft to review:
---
{draft_markdown}
---

Evaluate against the quality bar and the 6 failure modes listed."""

    raw = call_claude(system=CRITIQUE_SYSTEM, user=user_prompt, max_tokens=1000)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Critique stage returned non-JSON:\n{raw}") from e


REVISION_SYSTEM = """You are revising a technical blog post based on editor
feedback. Apply the revision instructions precisely. Preserve everything that
already works well. Output ONLY the revised Markdown post body, no preamble."""


def revise_draft(draft_markdown: str, revision_instructions: str) -> str:
    user_prompt = f"""Revision instructions:
{revision_instructions}

Original draft:
---
{draft_markdown}
---

Produce the revised post."""
    return call_claude(system=REVISION_SYSTEM, user=user_prompt, max_tokens=6000)
