"""
Publishes a Markdown post to dev.to via its public API.

This channel serves two purposes:
1. A standalone distribution channel in its own right.
2. The bridge into Medium: Medium closed new API integrations in 2023, so
   the supported path is to publish canonically elsewhere first, then use
   Medium's "Import a Story" tool (medium.com/p/import) pointing at the
   dev.to URL. Medium sets its canonical URL back to the original, so this
   doesn't hurt SEO. See medium_helper.py for that last (semi-manual) step.
"""
from __future__ import annotations

import os

import frontmatter
import requests

from src.utils.settings import get_settings

DEVTO_API = "https://dev.to/api/articles"


def publish_to_devto(markdown_path: str, canonical_url: str | None = None) -> dict:
    api_key = os.environ.get("DEVTO_API_KEY")
    if not api_key:
        raise RuntimeError("DEVTO_API_KEY is not set.")

    with open(markdown_path) as f:
        post = frontmatter.load(f)

    settings = get_settings()["publishing"]["devto"]

    payload = {
        "article": {
            "title": post.get("title"),
            "published": settings["publish_status"] == "public",
            "body_markdown": post.content,
            "tags": settings["tags"],
        }
    }
    if canonical_url:
        payload["article"]["canonical_url"] = canonical_url

    resp = requests.post(
        DEVTO_API,
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    print(f"[devto] Published: {data.get('url')}")
    return data


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.publishing.devto_publish <markdown_path> [canonical_url]")
        sys.exit(1)
    canonical = sys.argv[2] if len(sys.argv) > 2 else None
    publish_to_devto(sys.argv[1], canonical)
