"""
Takes raw candidates from arxiv/HN/GitHub and asks Claude to score them for
fit against the target pillar, then returns the single best topic with a
proposed angle. This is deliberately a *scoring* pass, not a summarization
pass — we want Claude to reject weak/generic candidates rather than write
about whatever came back first.
"""
from __future__ import annotations

import json

from src.sourcing.arxiv_source import fetch_arxiv_candidates
from src.sourcing.github_source import fetch_github_candidates
from src.sourcing.hn_source import fetch_hn_candidates
from src.utils.claude_client import call_claude

SCORER_SYSTEM = """You are the topic-selection editor for a senior-engineer-level \
Agentic AI blog. Your job is to reject generic or already-overdone topics and \
pick the ONE candidate (or a synthesis of a few) that would make the most useful, \
technically substantive, engaging post for a target pillar.

You are ruthless about avoiding:
- generic "what is agentic AI" explainer content
- rehashing a framework's own docs with no independent angle
- pure news reporting with no technical takeaway

You favor candidates that let the writer show real code, a real number, or a \
real opinion.

Respond ONLY with valid JSON, no markdown fences, no preamble, in this shape:
{
  "chosen_title_seed": "...",
  "angle": "one or two sentences on the specific angle/argument the post should take",
  "why": "one sentence on why this beats the other candidates",
  "supporting_source_urls": ["...", "..."]
}
"""


def gather_candidates(pillar: dict, per_source: int = 6) -> list[dict]:
    candidates: list[dict] = []
    for query in pillar["sourcing_queries"]:
        try:
            candidates += fetch_arxiv_candidates(query, max_results=per_source)
        except Exception as e:
            print(f"[sourcing] arxiv fetch failed for '{query}': {e}")
        try:
            candidates += fetch_hn_candidates(query, max_results=per_source)
        except Exception as e:
            print(f"[sourcing] HN fetch failed for '{query}': {e}")
        try:
            candidates += fetch_github_candidates(query, max_results=per_source)
        except Exception as e:
            print(f"[sourcing] GitHub fetch failed for '{query}': {e}")

    # de-dupe by title
    seen = set()
    deduped = []
    for c in candidates:
        key = c["title"].lower().strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(c)
    return deduped


def choose_topic(pillar: dict, is_contrarian: bool) -> dict:
    candidates = gather_candidates(pillar)
    if not candidates:
        raise RuntimeError(
            f"No candidates found for pillar '{pillar['id']}'. "
            "Check network access to arxiv/HN/GitHub, or widen sourcing_queries."
        )

    candidates_block = "\n".join(
        f"- [{c['source']}] {c['title']} — {c['summary']} ({c['url']})"
        for c in candidates[:40]  # cap prompt size
    )

    contrarian_instruction = (
        "\nThis post should take a deliberately contrarian or opinionated stance "
        "-- something a thoughtful practitioner could disagree with -- rather than "
        "a purely descriptive angle."
        if is_contrarian
        else ""
    )

    user_prompt = f"""Pillar: {pillar['name']}
Pillar brief: {pillar['description']}
{contrarian_instruction}

Candidate source material gathered in the last sourcing run:
{candidates_block}

Pick the single best topic (or synthesize two related candidates into one
sharper angle) for this pillar. Return the JSON object as instructed."""

    raw = call_claude(system=SCORER_SYSTEM, user=user_prompt, max_tokens=800)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Topic scorer returned non-JSON output:\n{raw}") from e

    result["pillar"] = pillar
    result["is_contrarian"] = is_contrarian
    return result
