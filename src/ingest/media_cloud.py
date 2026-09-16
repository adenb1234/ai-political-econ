"""Layer D — Media Cloud (free with API key) vs NewsBank (paid).

Media Cloud: https://www.mediacloud.org/ — account + key; default weekly quota.
Python client: pip install mediacloud

NewsBank Access World News: institutional / paid. DO NOT depend on it for the free backbone.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from ._download import ROOT, write_manifest

RAW_DIR = ROOT / "data" / "raw" / "media_cloud"
MC_DOCS = "https://www.mediacloud.org/"


def fetch() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("MC_API_KEY", "").strip()
    note = RAW_DIR / "ACCESS.md"
    note.write_text(
        "\n".join(
            [
                "# News layer access",
                "",
                "## Media Cloud (free complement)",
                f"- Site: {MC_DOCS}",
                "- Requires free account + MC_API_KEY for live queries.",
                "- Install: `pip install mediacloud`",
                "- Quota: check current FAQs (historically ~4k requests/week default).",
                "",
                "## NewsBank Access World News (paid)",
                "- Local-paper density similar to BBD state-level EPU corpus.",
                "- Institutional subscription required — optional enrichment only.",
                "- Free backbone must ship without NewsBank.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_manifest(
        "media_cloud",
        {
            "source_id": "media_cloud",
            "layer": "D",
            "docs": MC_DOCS,
            "status": "documented_only",
            "api_key_present": bool(key),
            "newsbank": {
                "status": "paid_excluded_from_backbone",
                "notes": "Do not gate free pipeline on NewsBank access.",
            },
            "notes": "No synthetic news rows. Wire SearchApi when MC_API_KEY is available.",
            "local_access_note": str(note.relative_to(ROOT)),
        },
    )
    print(f"Media Cloud: key={'yes' if key else 'no'}; notes at {note}")


def main() -> None:
    argparse.ArgumentParser().parse_args()
    fetch()


if __name__ == "__main__":
    main()
