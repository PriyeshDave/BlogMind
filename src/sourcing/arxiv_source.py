"""
Pulls recent arxiv papers relevant to a query. Uses arxiv's public Atom feed
API (no key required).
"""
from __future__ import annotations

import feedparser

ARXIV_API = "http://export.arxiv.org/api/query"


def fetch_arxiv_candidates(query: str, max_results: int = 8) -> list[dict]:
    """
    Returns a list of {title, summary, url, published} dicts, sorted by
    submission date descending.
    """
    params = (
        f"search_query=all:{query.replace(' ', '+')}"
        f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    )
    feed = feedparser.parse(f"{ARXIV_API}?{params}")

    candidates = []
    for entry in feed.entries:
        candidates.append(
            {
                "source": "arxiv",
                "title": entry.title.strip().replace("\n", " "),
                "summary": entry.summary.strip().replace("\n", " ")[:600],
                "url": entry.link,
                "published": entry.get("published", ""),
            }
        )
    return candidates
