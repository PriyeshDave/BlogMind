"""
Pulls recently-active, relevant GitHub repos via the public search API.
Unauthenticated requests are rate-limited to 10/min, which is plenty for a
job that runs once every 2 days. Set GH_TOKEN in the environment to raise
the limit if you also use this for other GitHub calls.
"""
from __future__ import annotations

import os

import requests

GITHUB_SEARCH_API = "https://api.github.com/search/repositories"


def fetch_github_candidates(query: str, max_results: int = 8) -> list[dict]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params = {
        "q": f"{query} pushed:>2026-01-01",
        "sort": "updated",
        "order": "desc",
        "per_page": max_results,
    }
    resp = requests.get(GITHUB_SEARCH_API, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    items = resp.json().get("items", [])

    candidates = []
    for item in items:
        candidates.append(
            {
                "source": "github",
                "title": item.get("full_name", ""),
                "summary": (item.get("description") or "")[:400],
                "url": item.get("html_url", ""),
                "published": item.get("updated_at", ""),
            }
        )
    return [c for c in candidates if c["title"]]
