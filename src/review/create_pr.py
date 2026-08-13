"""
Opens a GitHub PR containing a single generated draft, so review/edit/approve
happens through normal PR review (inline comments, suggested edits, merge =
approval). Intended to be called from generate-draft.yml after the branch +
commit have already been created by the workflow's git steps; this script
just handles the `gh pr create` call with a well-formatted body so the
reviewer sees the key metadata (pillar, contrarian flag, sources) without
opening the file.

Usage:
    python -m src.review.create_pr <path-to-draft.md> <branch-name>
"""
from __future__ import annotations

import subprocess
import sys

import frontmatter


def build_pr_body(post: frontmatter.Post) -> str:
    sources = post.get("sources", [])
    sources_block = "\n".join(f"- {s}" for s in sources) if sources else "_none logged_"

    return f"""## Draft ready for review

**Title:** {post.get('title')}
**Subtitle:** {post.get('subtitle')}
**Pillar:** {post.get('pillar')}
**Contrarian post:** {post.get('contrarian')}
**Generated at:** {post.get('generated_at')}

### Sources consulted during topic selection
{sources_block}

### Review checklist
- [ ] Concrete artifact present (code / real number / diagram)
- [ ] All factual claims and stats check out
- [ ] Code blocks are actually correct / runnable
- [ ] Matches blog voice (no AI-cliche phrasing left over)
- [ ] Title delivers on its promise

Merging this PR triggers `publish.yml`, which publishes to the site, dev.to,
and LinkedIn. Edit the file directly in this PR before merging if changes
are needed.
"""


def create_pr(draft_file: str, branch_name: str) -> None:
    with open(draft_file) as f:
        post = frontmatter.load(f)

    body = build_pr_body(post)
    title = f"Draft: {post.get('title', draft_file)}"

    subprocess.run(
        [
            "gh", "pr", "create",
            "--title", title,
            "--body", body,
            "--head", branch_name,
            "--base", "main",
            "--label", "blog-draft",
        ],
        check=True,
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m src.review.create_pr <draft.md> <branch-name>", file=sys.stderr)
        sys.exit(1)
    create_pr(sys.argv[1], sys.argv[2])
