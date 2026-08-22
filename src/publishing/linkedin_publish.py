"""
Publishes a text post (with link) to a personal LinkedIn profile using the
official LinkedIn Posts API (part of the Community Management API).

Requires: w_member_social scope, an access token, and the author's person
URN. See linkedin_oauth_helper.py for one-time setup.

Endpoint note: LinkedIn's current Posts API lives at /rest/posts. The older
/v2/posts and /v2/ugcPosts endpoints are from a previous API generation and
are not interchangeable with this one -- using them returns errors that
don't clearly say "wrong endpoint."

Article field note: LinkedIn does not scrape the target URL to build the
link preview. title and description must be supplied explicitly in
content.article, or LinkedIn may reject the post outright depending on API
version. source (the URL) alone is not sufficient.
"""
from __future__ import annotations

import os

import requests

LINKEDIN_POSTS_API = "https://api.linkedin.com/rest/posts"
LINKEDIN_VERSION = "202601"  # LinkedIn API version header (YYYYMM), bump periodically


def publish_to_linkedin(
    text: str,
    article_url: str,
    title: str | None = None,
    description: str | None = None,
    visibility: str = "PUBLIC",
) -> dict:
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    person_urn = os.environ.get("LINKEDIN_PERSON_URN")
    if not access_token or not person_urn:
        raise RuntimeError("LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_URN must be set.")

    article_content = {"source": article_url}
    if title:
        article_content["title"] = title[:200]  # LinkedIn caps article title length
    if description:
        article_content["description"] = description[:300]

    payload = {
        "author": person_urn,
        "commentary": text,
        "visibility": visibility,
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {"article": article_content},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "Linkedin-Version": LINKEDIN_VERSION,
    }

    resp = requests.post(LINKEDIN_POSTS_API, headers=headers, json=payload, timeout=30)

    if not resp.ok:
        # LinkedIn's error body almost always explains exactly what's wrong
        # (missing field, bad scope, expired token, etc.) -- surface it
        # instead of letting raise_for_status() hide it behind a bare 400.
        print(f"[linkedin] Request failed ({resp.status_code}): {resp.text}")
    resp.raise_for_status()

    post_id = resp.headers.get("x-restli-id", "")
    print(f"[linkedin] Published: {post_id}")
    return {"post_id": post_id, "status_code": resp.status_code}


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python -m src.publishing.linkedin_publish <text_file> <article_url>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        body_text = f.read()
    publish_to_linkedin(body_text, sys.argv[2])