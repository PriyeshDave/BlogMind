from __future__ import annotations

from src.generation.voice import VOICE_GUIDE
from src.utils.claude_client import call_claude_with_web_search

DRAFT_SYSTEM = f"""You are a senior AI engineer writing a technical blog post
for other senior engineers.
{VOICE_GUIDE}

You have access to a web_search tool. Use it to verify any specific claim,
statistic, framework behavior, or recent event before stating it as fact.
Do not state a specific number, benchmark, or "as of [date]" claim unless you
have searched and confirmed it. If you cannot verify a claim, either cut it
or clearly frame it as your own opinion/hypothesis rather than a fact.

Write the full post in Markdown. Follow the provided outline's structure and
section goals, but you may adjust section ordering if it improves flow.
Include real code blocks where the outline calls for a code artifact.

Output ONLY the Markdown post body. No preamble, no "Here is the post," no
closing meta-commentary."""


def generate_draft(topic: dict, outline: dict) -> str:
    sections_block = "\n".join(
        f"- {s['heading']}: {s['goal']}" for s in outline["sections"]
    )

    user_prompt = f"""Title: {outline['title']}
Subtitle: {outline['subtitle']}
Planned artifact: {outline['planned_artifact']}
Pillar: {topic['pillar']['name']}
Angle: {topic['angle']}
Contrarian post: {topic['is_contrarian']}

Section plan:
{sections_block}

Reference material gathered during topic selection (verify/expand via search,
don't just restate these):
{topic.get('supporting_source_urls', [])}

Write the full post now."""

    return call_claude_with_web_search(system=DRAFT_SYSTEM, user=user_prompt, max_tokens=6000)
