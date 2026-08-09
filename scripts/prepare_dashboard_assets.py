"""Copy the multi-page dashboard source into the GitHub Pages artifact."""

from __future__ import annotations

import shutil
from pathlib import Path

SOURCE = Path("dashboard")
PUBLIC = Path("public")
PAGE_NAMES = ("index.html", "diarization.html", "workflows.html", "evidence.html", "guide.html")
ASSET_NAMES = ("app.css", "app.js", "bg-music.mp3", "favicon.png", "favicon.webp")


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in (*PAGE_NAMES, *ASSET_NAMES):
        source = SOURCE / name
        if not source.is_file():
            if name.endswith(".webp"):
                continue
            raise FileNotFoundError(f"Required dashboard source is missing: {source}")
        shutil.copy2(source, PUBLIC / name)
        copied.append(name)
    (PUBLIC / ".nojekyll").touch()
    print(f"Prepared Dashboard v6: {', '.join(copied)}")


if __name__ == "__main__":
    main()
