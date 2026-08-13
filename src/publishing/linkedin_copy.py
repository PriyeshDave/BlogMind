"""
Generates a short, LinkedIn-native post (hook + key insight + link) from
the full blog post. LinkedIn rewards native text over "read my blog" links
with no context, so this is a distinct piece of copy, not just a truncation
of the post.
"""
from __future__ import annotations

from src.utils.claude_client import call_claude

LINKEDIN_COPY_SYSTEM = """You write short LinkedIn posts that promote a
technical blog post you just published. Rules:

- 3-6 short paragraphs, LinkedIn-native formatting (short lines, no markdown
  headers, minimal hashtags -- 3 max at the very end)
- Open with a specific, concrete hook (a number, a surprising claim, or a
  sharp question) -- never "Excited to share my latest post"
- Convey the single most useful insight from the post directly in the
  LinkedIn text itself, don't make the reader click through to get any value
- End with a one-line reason to click the link, then the link on its own line
- No emojis except at most one, and only if it earns its place
- Match the voice of a senior engineer, not a marketer"""


def generate_linkedin_copy(post_markdown: str, post_url: str) -> str:
    user_prompt = f"""Blog post URL: {post_url}

Full post content:
---
{post_markdown}
---

Write the LinkedIn post."""
    return call_claude(system=LINKEDIN_COPY_SYSTEM, user=user_prompt, max_tokens=600)
