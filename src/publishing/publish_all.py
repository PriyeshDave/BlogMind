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


def canonical_url_for(post: frontmatter.Post) -> str:
    base = os.environ.get("SITE_BASE_URL", "https://yourblog.example.com")
    slug = slugify(post.get("title", "post"))
    return f"{base.rstrip('/')}/{slug}"


def publish_all(draft_path: str, dry_run: bool = False) -> None:
    published_path = move_to_published(draft_path)
    with open(published_path) as f:
        post = frontmatter.load(f)

    canonical_url = canonical_url_for(post)
    print(f"[publish_all] Canonical URL (your site): {canonical_url}")

    if dry_run:
        print("[publish_all] DRY RUN — skipping actual publish calls.")
        return

    # 1. dev.to
    devto_result = publish_to_devto(str(published_path), canonical_url=canonical_url)
    devto_url = devto_result.get("url", "")

    # 2. Medium (semi-manual bridge via dev.to)
    print(build_import_instructions(devto_url))
    open_import_page(devto_url)

    # 3. LinkedIn
    linkedin_text = generate_linkedin_copy(post.content, canonical_url)
    publish_to_linkedin(linkedin_text, canonical_url)

    print("[publish_all] Done. Site publish still needs your static site build/"
          "deploy step to pick up content/published/ — wire that into your "
          "site repo's own CI if it's separate from this repo.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("draft_path")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    publish_all(args.draft_path, dry_run=args.dry_run)
