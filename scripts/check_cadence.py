"""
GitHub Actions cron doesn't have a native "every N days" schedule that
survives daylight savings / month boundaries cleanly, so this workflow runs
daily and self-throttles using the last-run timestamp stored in
content/.pipeline_state.json.

Writes `should_run=true|false` to $GITHUB_OUTPUT.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# This script is invoked directly (`python scripts/check_cadence.py`), which
# only puts scripts/ on sys.path -- not the repo root. Add the repo root
# explicitly so `from src.utils...` resolves regardless of invocation style
# or working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.settings import get_settings
from src.utils.storage import load_state, save_state


def main() -> None:
    settings = get_settings()
    state = load_state()

    last_run_iso = state.get("last_run_at")
    should_run = True

    if last_run_iso:
        last_run = datetime.fromisoformat(last_run_iso)
        elapsed_days = (datetime.now(timezone.utc) - last_run).days
        should_run = elapsed_days >= settings["cadence_days"]

    # Manual override for testing: set FORCE_RUN=true (wired to a
    # workflow_dispatch input) to bypass the cadence check entirely.
    if os.environ.get("FORCE_RUN", "").lower() == "true":
        should_run = True
        print("[cadence] FORCE_RUN=true — bypassing cadence check.")

    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a") as f:
            f.write(f"should_run={'true' if should_run else 'false'}\n")

    print(f"[cadence] last_run_at={last_run_iso} should_run={should_run}")

    if should_run:
        state["last_run_at"] = datetime.now(timezone.utc).isoformat()
        save_state(state)


if __name__ == "__main__":
    main()