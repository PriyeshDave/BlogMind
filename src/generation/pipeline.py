"""
Entry point for draft generation. Run as:

    python -m src.generation.pipeline

Sources a topic for the next pillar in rotation, runs it through
outline -> draft -> critique -> (optional revision) -> style pass, and
writes the result to content/drafts/ as a Markdown file with YAML
frontmatter. This file is what generate-draft.yml commits and opens a PR
for.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

import frontmatter

from src.generation.critique import critique_draft, revise_draft
from src.generation.outline import generate_outline
from src.generation.draft import generate_draft
from src.generation.style_pass import style_pass
from src.sourcing.topic_scorer import choose_topic
from src.utils.storage import draft_path, load_state, next_pillar, save_state

MAX_REVISION_ROUNDS = 2


def run_pipeline() -> str:
    state = load_state()
    pillar, is_contrarian = next_pillar(state)

    print(f"[pipeline] Pillar: {pillar['name']} | contrarian: {is_contrarian}")

    print("[pipeline] Sourcing + scoring topic...")
    topic = choose_topic(pillar, is_contrarian)
    print(f"[pipeline] Chosen angle: {topic['angle']}")

    print("[pipeline] Generating outline...")
    outline = generate_outline(topic)
    print(f"[pipeline] Title: {outline['title']}")

    print("[pipeline] Generating draft (with web search grounding)...")
    draft_md = generate_draft(topic, outline)

    for round_num in range(1, MAX_REVISION_ROUNDS + 1):
        print(f"[pipeline] Critique round {round_num}...")
        review = critique_draft(draft_md)
        if review["passes_quality_bar"]:
            print("[pipeline] Passed quality bar.")
            break
        print(f"[pipeline] Issues found: {review['issues']}")
        draft_md = revise_draft(draft_md, review["revision_instructions"])
    else:
        print("[pipeline] WARNING: did not pass quality bar after max revisions. "
              "Flagging for extra-careful human review.")

    print("[pipeline] Running style pass...")
    final_md = style_pass(draft_md)

    post = frontmatter.Post(final_md)
    post["title"] = outline["title"]
    post["subtitle"] = outline["subtitle"]
    post["pillar"] = pillar["id"]
    post["contrarian"] = is_contrarian
    post["generated_at"] = datetime.now(timezone.utc).isoformat()
    post["status"] = "pending_review"
    post["sources"] = topic.get("supporting_source_urls", [])

    out_path = draft_path(outline["title"])
    with open(out_path, "w") as f:
        frontmatter.dump(post, f)

    save_state(state)
    print(f"[pipeline] Draft written to {out_path}")
    return str(out_path)


if __name__ == "__main__":
    try:
        path = run_pipeline()
        print(path)
    except Exception as e:
        print(f"[pipeline] FAILED: {e}", file=sys.stderr)
        sys.exit(1)
