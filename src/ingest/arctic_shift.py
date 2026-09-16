"""Layer F — Arctic Shift Reddit historical dumps.

Repo: https://github.com/ArthurHeitmann/arctic_shift
Links: https://github.com/ArthurHeitmann/arctic_shift/blob/master/download_links.md

Dumps are multi-GB torrents (Academic Torrents). This module records access notes only.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ._download import ROOT, write_manifest

REPO = "https://github.com/ArthurHeitmann/arctic_shift"
LINKS = "https://github.com/ArthurHeitmann/arctic_shift/blob/master/download_links.md"
RAW_DIR = ROOT / "data" / "raw" / "arctic_shift"


def fetch() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    readme = RAW_DIR / "ACCESS.md"
    readme.write_text(
        "\n".join(
            [
                "# Arctic Shift access",
                "",
                f"- Repo: {REPO}",
                f"- Download links: {LINKS}",
                "- Method: Academic Torrents / HTTP mirrors listed upstream; prefer dumps for backfill.",
                "- Ongoing: official Reddit API (OAuth) — separate from Arctic Shift.",
                "- Do not commit dump files; keep under data/raw/arctic_shift/ and gitignore.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_manifest(
        "arctic_shift",
        {
            "source_id": "arctic_shift",
            "layer": "F",
            "repo": REPO,
            "download_links": LINKS,
            "status": "documented_only",
            "blocker": "Torrent/HTTP dumps are multi-GB to multi-TB; not auto-mirrored in scaffold",
            "notes": "Crosswalk city/regional subreddits to county FIPS is a separate geo table.",
            "local_access_note": str(readme.relative_to(ROOT)),
        },
    )
    print(f"Arctic Shift notes written to {readme}")


def main() -> None:
    argparse.ArgumentParser().parse_args()
    fetch()


if __name__ == "__main__":
    main()
