"""
Publishes a text post (with link) to a personal LinkedIn profile using the
official LinkedIn Posts API (part of the Community Management API).

Requires: w_member_social scope, an access token, and the author's person
URN. See linkedin_oauth_helper.py for one-time setup.
"""
from __future__ import annotations

import os

import requests

LINKEDIN_POSTS_API = "https://api.linkedin.com/v2/posts"
LINKEDIN_VERSION = "202601"  # LinkedIn API version header, bump periodically


def publish_to_linkedin(text: str, article_url: str, visibility: str = "PUBLIC") -> dict:
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    person_urn = os.environ.get("LINKEDIN_PERSON_URN")
    if not access_token or not person_urn:
        raise RuntimeError("LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_URN must be set.")

    payload = {
        "author": person_urn,
        "commentary": text,
        "visibility": visibility,
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {
            "article": {
                "source": article_url,
            }
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": LINKEDIN_VERSION,
    }

    resp = requests.post(LINKEDIN_POSTS_API, headers=headers, json=payload, timeout=30)
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
