from __future__ import annotations

from src.generation.voice import VOICE_GUIDE
from src.utils.claude_client import call_claude

STYLE_SYSTEM = f"""You are a copy editor doing a final voice/style pass on a
technical blog post. Do NOT change the technical content, claims, code, or
structure. Only tighten prose to match this voice guide:
{VOICE_GUIDE}

Specifically: cut hedging phrases, remove AI-cliche transitions ("in
conclusion", "let's dive in", "it's worth noting"), tighten sentences, and
make subheadings specific rather than generic. Output ONLY the final
Markdown post body, no preamble."""


def style_pass(draft_markdown: str) -> str:
    return call_claude(system=STYLE_SYSTEM, user=draft_markdown, max_tokens=6000)
