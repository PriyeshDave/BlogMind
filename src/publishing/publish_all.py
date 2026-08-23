"""
Runs the full publish sequence for one approved post:

  1. Moves the file from content/drafts/ to content/published/ (this becomes
     the canonical source your own Astro/Next.js site reads from)
  2. Publishes to dev.to, with canonical_url pointing at your own site
  3. Prints/opens Medium's Import Story instructions pointing at the dev.to URL
  4. Generates LinkedIn-native copy and posts it with a link back to your site

Usage:
    python -m src.publishing.publish_all content/drafts/2026-08-14-example.md

Intended to be called by publish.yml on merge to main, but safe to run
locally against any draft file for testing (dry-run flag available).
"""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

import frontmatter

from src.publishing.devto_publish import publish_to_devto
from src.publishing.linkedin_copy import generate_linkedin_copy
from src.publishing.linkedin_publish import publish_to_linkedin
from src.publishing.medium_helper import build_import_instructions, open_import_page
from src.utils.settings import get_settings
from src.utils.storage import REPO_ROOT, slugify


def move_to_published(draft_path: str) -> Path:
    settings = get_settings()
    published_dir = REPO_ROOT / settings["published_dir"]
    published_dir.mkdir(parents=True, exist_ok=True)

    src = Path(draft_path)
    dest = published_dir / src.name
    shutil.move(str(src), str(dest))

    with open(dest) as f:
        post = frontmatter.load(f)
    post["status"] = "published"
    with open(dest, "w") as f:
        frontmatter.dump(post, f)

    return dest


def has_real_site() -> bool:
    """
    Returns False if SITE_BASE_URL is unset or still the placeholder value —
    meaning your own static site isn't live yet. In that case dev.to becomes
    the canonical source for this post instead, so LinkedIn/Medium don't
    link to a domain that doesn't resolve.

    Once your Astro/Next.js site is deployed, set SITE_BASE_URL to the real
    domain and this pipeline automatically switches canonical ownership back
    to your own site for future posts.
    """
    base = os.environ.get("SITE_BASE_URL", "")
    return bool(base) and "yourblog.example.com" not in base


def canonical_url_for(post: frontmatter.Post) -> str:
    base = os.environ.get("SITE_BASE_URL", "https://yourblog.example.com")
    slug = slugify(post.get("title", "post"))
    return f"{base.rstrip('/')}/{slug}"


def publish_all(draft_path: str, dry_run: bool = False) -> None:
    published_path = move_to_published(draft_path)
    with open(published_path) as f:
        post = frontmatter.load(f)

    site_is_live = has_real_site()

    if site_is_live:
        canonical_url = canonical_url_for(post)
        print(f"[publish_all] Canonical URL (your site): {canonical_url}")
    else:
        canonical_url = None
        print(
            "[publish_all] No live SITE_BASE_URL set — dev.to will be the "
            "canonical source for this post until your own site is deployed."
        )

    if dry_run:
        print("[publish_all] DRY RUN — skipping actual publish calls.")
        return

    # 1. dev.to — only pass canonical_url if your own site is live; otherwise
    # dev.to owns canonicality for this post.
    devto_result = publish_to_devto(str(published_path), canonical_url=canonical_url)
    devto_url = devto_result.get("url", "")

    # If no site yet, everything downstream links to the dev.to URL instead.
    link_target = canonical_url if site_is_live else devto_url

    # 2. Medium (semi-manual bridge via dev.to)
    print(build_import_instructions(devto_url))
    open_import_page(devto_url)

    # 3. LinkedIn
    linkedin_settings = get_settings()["publishing"]["linkedin"]
    linkedin_text = generate_linkedin_copy(
        post.content,
        devto_url=devto_url,
        intro_post_url=linkedin_settings["intro_post_url"],
    )
    publish_to_linkedin(
        linkedin_text,
        link_target,
        title=post.get("title"),
        description=post.get("subtitle"),
    )

    if site_is_live:
        print("[publish_all] Done. Site publish still needs your static site build/"
              "deploy step to pick up content/published/ — wire that into your "
              "site repo's own CI if it's separate from this repo.")
    else:
        print(f"[publish_all] Done. dev.to is canonical for now: {devto_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("draft_path")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    publish_all(args.draft_path, dry_run=args.dry_run)