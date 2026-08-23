"""
Generates a short, LinkedIn-native post (hook + key insight + link) from
the full blog post. LinkedIn rewards native text over "read my blog" links
with no context, so this is a distinct piece of copy, not just a truncation
of the post.

Design note: earlier versions asked the LLM to produce the entire formatted
post as free text, including mandatory hashtags and specific structure. That
proved unreliable -- the model would drop hashtags or collapse everything
into dense paragraphs despite explicit instructions. This version asks the
LLM only for the *content* (headline, context, insight bullets, hashtags) as
structured JSON, then assembles the final post deterministically in Python.
Formatting, links, and attribution are never left to chance.
"""
from __future__ import annotations

import json

from src.utils.claude_client import call_claude

LINKEDIN_COPY_SYSTEM = """You extract the content for a LinkedIn post
promoting a technical blog post you just published. You are NOT responsible
for final formatting -- just for picking the right content.

Respond ONLY with valid JSON, no markdown fences, in this shape:
{
  "headline": "a punchy, specific headline for the post, under 12 words -- \
this is NOT the blog post's title verbatim, it's a hook",
  "context_lines": [
    "1-2 sentences explaining what this post is actually about and why it \
matters -- a reader who hasn't clicked anything yet must understand the \
core argument from this alone",
    "optionally one more sentence of context if needed"
  ],
  "insight_bullets": [
    "3-5 short, specific, standalone findings/claims/numbers from the post, \
each under 20 words, each usable as its own line"
  ],
  "hashtags": ["#Exactly", "#Three", "#RelevantSpecificHashtags"]
}

Rules:
- The headline and context together must let someone understand the post's
  actual argument without clicking through -- never just tease one isolated
  stat with no explanation of what it's from or why it matters.
- insight_bullets must be genuinely informative on their own, not vague
  teasers ("you won't believe what we found" is banned).
- hashtags must be specific to this post's actual topic, never generic
  filler like #AI or #innovation.
- Match the voice of a senior engineer, not a marketer."""


def _to_bold_unicode(text: str) -> str:
    """
    LinkedIn has no native text formatting (no markdown bold). This maps
    ASCII letters/digits to the Unicode "Mathematical Bold" block, which
    LinkedIn (and most platforms) render as visually bold characters --
    the same trick real LinkedIn headline posts use. Non-alphanumeric
    characters (spaces, punctuation) pass through unchanged.
    """
    result = []
    for ch in text:
        if "A" <= ch <= "Z":
            result.append(chr(0x1D400 + (ord(ch) - ord("A"))))
        elif "a" <= ch <= "z":
            result.append(chr(0x1D41A + (ord(ch) - ord("a"))))
        elif "0" <= ch <= "9":
            result.append(chr(0x1D7CE + (ord(ch) - ord("0"))))
        else:
            result.append(ch)
    return "".join(result)


def generate_linkedin_copy(post_markdown: str, devto_url: str, intro_post_url: str) -> str:
    """
    devto_url: link to the specific blog post being promoted. NOT embedded
        as raw text in the post body -- it's attached separately via
        publish_to_linkedin's content.article.source, which renders as a
        proper preview card (title, description, thumbnail). Kept as a
        parameter here for logging/future use, not string interpolation.
    intro_post_url: link to your "how BlogMind works" post. Also NOT
        embedded as raw text for the same reason (see note below).

    Why no raw URLs in the body: LinkedIn's Posts API silently truncates
    the commentary text at the point a raw URL appears when that URL
    duplicates the one already attached via content.article -- confirmed
    by LinkedIn's own help docs, which note that a shared link with no
    text after it gets hidden from the share entirely. In practice this
    meant everything after "Read the full breakdown: <url>" was silently
    dropped from the live post, even on the post's own permalink page.
    The safe fix is to never put a raw URL in the commentary body at all;
    the attached article card already gives readers a click-through.
    """
    user_prompt = f"""Full blog post content:
---
{post_markdown}
---

Extract the headline, context, insight bullets, and hashtags as instructed."""

    raw = call_claude(system=LINKEDIN_COPY_SYSTEM, user=user_prompt, max_tokens=700)

    try:
        parts = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LinkedIn copy stage returned non-JSON:\n{raw}") from e

    headline = _to_bold_unicode(parts["headline"])
    context = "\n".join(parts["context_lines"])
    bullets = "\n".join(f"- {b}" for b in parts["insight_bullets"])
    hashtags = " ".join(parts["hashtags"][:3])

    post = f"""{headline}

{context}

{bullets}

🧠 Researched, drafted, and published by BlogMind — My AI-Powered Content Automation System (research -> source → draft → critique → human review → publish).

{hashtags}"""

    return post