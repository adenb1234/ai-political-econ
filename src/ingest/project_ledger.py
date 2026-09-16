"""Layer G — open data-center / interconnection source index (no invented projects).

Wired free pull: EIA-861 via eia_861.py.
Also document LBNL Queued Up + ISO queue portals for later fetchers.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ._download import ROOT, write_manifest

RAW_DIR = ROOT / "data" / "raw" / "eia"


def fetch() -> None:
    write_manifest(
        "project_ledger_sources",
        {
            "source_id": "project_ledger_sources",
            "layer": "G",
            "status": "index",
            "sources": [
                {
                    "name": "EIA-861",
                    "url": "https://www.eia.gov/electricity/data/eia861/",
                    "fetcher": "src/ingest/eia_861.py",
                    "access": "public domain, no key",
                },
                {
                    "name": "LBNL Queued Up",
                    "url": "https://emp.lbl.gov/queues",
                    "access": "free XLSX editions; check current publication page",
                    "notes": "Generation/storage interconnection — not load/data-center permits",
                },
                {
                    "name": "ISO/RTO queues",
                    "examples": ["PJM", "MISO", "CAISO", "ERCOT", "NYISO", "ISO-NE", "SPP"],
                    "access": "per-ISO open data portals; schemas differ",
                },
                {
                    "name": "National data-center permit registry",
                    "access": "does not exist — coverage is whatever we build (WORKING_SPEC)",
                },
            ],
            "notes": "Denominator layer. Never invent proposed/approved/denied counts.",
        },
    )
    print(f"Layer G source index written; EIA raw dir={RAW_DIR}")


def main() -> None:
    argparse.ArgumentParser().parse_args()
    fetch()


if __name__ == "__main__":
    main()
