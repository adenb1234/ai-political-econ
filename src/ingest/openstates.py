"""Layer B complement — Open States v3.

Docs: https://docs.openstates.org/
API key required for production GraphQL/REST. No credential-free national bill dump.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from ._download import ROOT, write_manifest

DOCS = "https://docs.openstates.org/"
RAW_DIR = ROOT / "data" / "raw" / "openstates"


def fetch() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("OPENSTATES_API_KEY", "").strip()
    write_manifest(
        "openstates",
        {
            "source_id": "openstates",
            "layer": "B",
            "docs": DOCS,
            "status": "documented_only",
            "api_key_present": bool(key),
            "notes": (
                "Use for committee detail beyond LegiScan. "
                "Set OPENSTATES_API_KEY to enable live pulls in a later phase. "
                "Public docs only in this scaffold — no fabricated legislative sample."
            ),
            "license_note": "Open States terms / CC depending on endpoint",
        },
    )
    print(f"Open States: key={'yes' if key else 'no'}; docs={DOCS}")


def main() -> None:
    argparse.ArgumentParser().parse_args()
    fetch()


if __name__ == "__main__":
    main()
