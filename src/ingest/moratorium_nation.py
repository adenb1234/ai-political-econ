"""Layer C — Moratorium Nation free inventory CSVs (CC BY 4.0)."""

from __future__ import annotations

import argparse
from pathlib import Path

from ._download import ROOT, try_download

PORTAL = "https://mjbommar.github.io/moratorium-data-2026/"
REPO = "https://github.com/mjbommar/moratorium-data-2026"
DATA_INDEX = "https://mjbommar.github.io/moratorium-data-2026/data/index.html"

INVENTORY_URL = (
    "https://raw.githubusercontent.com/mjbommar/moratorium-data-2026/main/"
    "data/moratorium_inventory.csv"
)
STATE_LEG_URL = (
    "https://raw.githubusercontent.com/mjbommar/moratorium-data-2026/main/"
    "data/state_legislation.csv"
)

DEST_INVENTORY = ROOT / "data" / "raw" / "moratorium_nation" / "moratorium_inventory.csv"
DEST_STATE_LEG = ROOT / "data" / "raw" / "moratorium_nation" / "state_legislation.csv"


def fetch(force: bool = False) -> list[Path]:
    out: list[Path] = []
    jobs = [
        (
            INVENTORY_URL,
            DEST_INVENTORY,
            "moratorium_nation_inventory",
            "Moratorium Nation local-moratorium inventory (533 instruments). "
            "Layer C ordinances/moratoria. Do not invent rows.",
        ),
        (
            STATE_LEG_URL,
            DEST_STATE_LEG,
            "moratorium_nation_state_legislation",
            "Moratorium Nation state legislation companion (2025–2026 bills/actions). "
            "Layer C adjunct / B overlap. Do not invent rows.",
        ),
    ]
    for url, dest, sid, notes in jobs:
        if dest.exists() and not force:
            print(f"already present: {dest} ({dest.stat().st_size} bytes)")
            out.append(dest)
            continue
        ok, msg = try_download(
            url,
            dest,
            source_id=sid,
            notes=notes,
            license_note="CC BY 4.0 (Moratorium Nation / mjbommar)",
            extra={
                "layer": "C",
                "portal": PORTAL,
                "repo": REPO,
                "data_index": DATA_INDEX,
                "access_date_pt": "2026-09-16",
            },
        )
        print(msg)
        if not ok:
            raise SystemExit(1)
        out.append(dest)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch Moratorium Nation free CSVs")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    fetch(force=args.force)


if __name__ == "__main__":
    main()
