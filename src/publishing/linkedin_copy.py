"""
Generates a short, LinkedIn-native post (hook + key insight + link) from
the full blog post. LinkedIn rewards native text over "read my blog" links
with no context, so this is a distinct piece of copy, not just a truncation
of the post.
"""
from __future__ import annotations

from src.utils.claude_client import call_claude

LINKEDIN_COPY_SYSTEM = """You write short LinkedIn posts that promote a
technical blog post you just published.

FORMATTING RULES (strict, non-negotiable):
- Every line is 1-2 sentences MAX. Never write a paragraph of 3+ sentences
  stacked together -- LinkedIn has no markdown, so visual whitespace is the
  ONLY formatting tool available. Break generously.
- Leave a blank line between every distinct idea/beat. The post should look
  like a stack of short blocks, not paragraphs.
- When listing findings, comparisons, or numbers (e.g. "X vs Y vs Z"), put
  EACH one on its own line prefixed with a plain dash "- ", not folded into
  a sentence. Example:
  - AutoGen: 90% success, ~10s/task
  - LangGraph: 78% success, ~13s/task
  - CrewAI: 71% success, ~20s/task
- MANDATORY: end with exactly 3 hashtags relevant to the specific post's
  topic (not generic filler like #AI or #innovation) on their own final
  line. This is required on every post, not optional.
- Open with a specific, concrete hook (a number, a surprising claim, or a
  sharp question) -- never "Excited to share my latest post."
- Convey the single most useful insight from the post directly in the
  LinkedIn text itself, don't make the reader click through to get any value.
- End the body (before the hashtags) with a one-line reason to click, then
  the link on its own line.
- No emojis except at most one, and only if it earns its place.
- Match the voice of a senior engineer, not a marketer.

Target total length: 130-200 words in the body, before hashtags."""


def generate_linkedin_copy(post_markdown: str, post_url: str) -> str:
    user_prompt = f"""Blog post URL: {post_url}

Full post content:
---
{post_markdown}
---

Write the LinkedIn post, following the formatting rules exactly -- short
lines, blank lines between beats, dash-prefixed list for any comparison
data, and exactly 3 relevant hashtags on the final line."""
    return call_claude(system=LINKEDIN_COPY_SYSTEM, user=user_prompt, max_tokens=700)