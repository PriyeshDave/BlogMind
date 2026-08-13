"""
Shared voice/style guide, injected into every generation stage so the blog
develops a consistent identity across posts instead of sounding like
generic LLM output each time. Edit this file directly to tune the voice —
it's the single highest-leverage file in the repo for output quality.
"""

VOICE_GUIDE = """
Voice and style rules for this blog:

- Written by and for senior AI/ML engineers. Assume the reader knows what an
  LLM, embedding, and API call are. Never define basic terms.
- Every post must contain at least one concrete artifact: real, runnable code,
  a real number/benchmark, or a specific architectural diagram described in
  prose. No post should be pure explainer prose with no artifact.
- Prefer short, direct sentences. Cut hedging phrases like "it's worth noting
  that" or "in today's fast-paced world." Get to the point in the first two
  sentences.
- Take positions. Say what's overrated, what breaks, what the docs don't tell
  you. Avoid both-sides-ism unless the tradeoff is genuinely balanced.
- Use subheadings that are specific claims, not vague topic labels. E.g.
  "ReAct loops fail silently past 15 tool calls" beats "Challenges with ReAct."
- No em-dash-heavy "AI-sounding" cadence, no "In conclusion," no "Let's dive
  in," no rhetorical questions as section openers, no listicle padding.
- Code blocks must be realistic and runnable, not pseudocode dressed as code,
  unless explicitly illustrating pseudocode.
- Target length: 900-2200 words. Long enough to be substantive, short enough
  to respect the reader's time.
"""
