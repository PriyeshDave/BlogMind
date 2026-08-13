from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.utils.settings import get_pillars, get_settings

REPO_ROOT = Path(__file__).resolve().parents[2]


def _state_path() -> Path:
    return REPO_ROOT / get_settings()["state_file"]


def load_state() -> dict:
    path = _state_path()
    if not path.exists():
        return {"post_count": 0, "last_pillar_index": -1, "published": []}
    with open(path) as f:
        return json.load(f)


def save_state(state: dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def next_pillar(state: dict) -> tuple[dict, bool]:
    """
    Returns (pillar_dict, is_contrarian) for the next post in rotation,
    and advances the rotation index. Does NOT persist — caller should
    save_state() once the post is actually generated successfully.
    """
    pillars = get_pillars()
    settings = get_settings()

    idx = (state["last_pillar_index"] + 1) % len(pillars)
    pillar = pillars[idx]

    post_number = state["post_count"] + 1
    is_contrarian = post_number % settings["contrarian_every"] == 0

    state["last_pillar_index"] = idx
    state["post_count"] = post_number
    return pillar, is_contrarian


def slugify(title: str) -> str:
    keep = [c.lower() if c.isalnum() else "-" for c in title]
    slug = "".join(keep)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:80]


def draft_path(title: str) -> Path:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = slugify(title)
    drafts_dir = REPO_ROOT / get_settings()["drafts_dir"]
    drafts_dir.mkdir(parents=True, exist_ok=True)
    return drafts_dir / f"{date_str}-{slug}.md"
