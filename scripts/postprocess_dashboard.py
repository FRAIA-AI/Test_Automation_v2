"""Validate the deterministic multi-page dashboard build."""

from __future__ import annotations

from pathlib import Path

PAGES = ("index.html", "diarization.html", "workflows.html", "evidence.html", "guide.html")


def main() -> None:
    for page in PAGES:
        html = (Path("public") / page).read_text(encoding="utf-8")
        if 'id="app"' not in html or "app.css" not in html or "app.js" not in html:
            raise RuntimeError(f"Dashboard v5 shell is incomplete: {page}")
    print("Validated Dashboard v5 multi-page command center.")


if __name__ == "__main__":
    main()
