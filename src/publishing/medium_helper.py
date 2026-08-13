"""
Medium closed its public API to new integrations in 2023 (no new integration
tokens are issued). There is no fully-automatable path for a new integration.

The supported workaround: publish canonically elsewhere (this pipeline uses
dev.to, see devto_publish.py), then use Medium's own "Import a Story" tool,
which fetches the article by URL and preserves the canonical link back to
the original for SEO.

This helper does the one step that *is* automatable — generating the
correctly-formed import URL and, when run locally (not in CI), opening it in
your browser so the only manual action left is clicking "Import" and hitting
publish on Medium's side.
"""
from __future__ import annotations

import sys
import webbrowser
from urllib.parse import quote

MEDIUM_IMPORT_BASE = "https://medium.com/p/import"


def build_import_instructions(devto_url: str) -> str:
    return f"""Medium import step (manual, ~30 seconds):

1. Go to: {MEDIUM_IMPORT_BASE}
2. Paste this URL when prompted: {devto_url}
3. Medium will pull the title, body, and images, and set the canonical URL
   back to dev.to automatically.
4. Review formatting (Medium sometimes needs a manual nudge on code block
   styling) and hit Publish.
"""


def open_import_page(devto_url: str) -> None:
    """Best-effort: opens the Medium import tool in a local browser. This is
    a no-op / silently skipped in CI environments with no display."""
    try:
        webbrowser.open(f"{MEDIUM_IMPORT_BASE}?url={quote(devto_url, safe='')}")
    except Exception:
        pass  # headless CI environment — instructions were already printed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m src.publishing.medium_helper <devto_url>", file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    print(build_import_instructions(url))
    open_import_page(url)
