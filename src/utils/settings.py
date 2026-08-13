from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


@lru_cache(maxsize=1)
def get_settings() -> dict:
    with open(CONFIG_DIR / "settings.yaml") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def get_pillars() -> list[dict]:
    with open(CONFIG_DIR / "pillars.yaml") as f:
        data = yaml.safe_load(f)
    return data["pillars"]
