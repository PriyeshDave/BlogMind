from __future__ import annotations

import json

from src.generation.voice import VOICE_GUIDE
from src.utils.claude_client import call_claude

OUTLINE_SYSTEM = f"""You are a senior AI engineer planning a technical blog post.
{VOICE_GUIDE}

Respond ONLY with valid JSON, no markdown fences, in this shape:
{{
  "title": "specific, non-generic title",
  "subtitle": "one sentence promise of what the reader will walk away with",
  "sections": [
    {{"heading": "...", "goal": "what this section must accomplish/prove"}}
  ],
  "planned_artifact": "description of the concrete code/data/diagram this post will include"
}}
"""


def generate_outline(topic: dict) -> dict:
    user_prompt = f"""Pillar: {topic['pillar']['name']}
Angle: {topic['angle']}
Why this angle: {topic['why']}
Contrarian post: {topic['is_contrarian']}
Source material: {topic.get('supporting_source_urls', [])}
Seed title idea: {topic['chosen_title_seed']}

Plan the outline for this post."""

    raw = call_claude(system=OUTLINE_SYSTEM, user=user_prompt, max_tokens=1200)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Outline stage returned non-JSON:\n{raw}") from e
