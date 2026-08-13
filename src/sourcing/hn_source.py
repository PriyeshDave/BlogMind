"""
Pulls relevant, currently-popular Hacker News discussions via the free
Algolia HN Search API (no key required). Good signal for "what practitioners
are actually arguing about right now."
"""
from __future__ import annotations

import requests

HN_ALGOLIA_API = "https://hn.algolia.com/api/v1/search"


def fetch_hn_candidates(query: str, max_results: int = 8) -> list[dict]:
    params = {
        "query": query,
        "tags": "story",
        "numericFilters": "points>20",
        "hitsPerPage": max_results,
    }
    resp = requests.get(HN_ALGOLIA_API, params=params, timeout=15)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])

    candidates = []
    for hit in hits:
        candidates.append(
            {
                "source": "hackernews",
                "title": hit.get("title") or "",
                "summary": f"{hit.get('points', 0)} points, "
                f"{hit.get('num_comments', 0)} comments",
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                "published": hit.get("created_at", ""),
            }
        )
    return [c for c in candidates if c["title"]]
