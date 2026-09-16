"""Layer G — LBNL Queued Up interconnection queue workbook (CC BY 4.0).

Generation/storage queues only — NOT a data-center permit registry.
Do not invent proposed/approved/denied data-center counts from this file.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ._download import ROOT, try_download

XLSX_URL = (
    "https://emp.lbl.gov/sites/default/files/2026-05/"
    "LBNL_Ix_Queue_Data_File_thru2025.xlsx"
)
DEST = ROOT / "data" / "raw" / "lbnl" / "LBNL_Ix_Queue_Data_File_thru2025.xlsx"
PORTAL = "https://emp.lbl.gov/queues"
PUB_NOTE = (
    "LBNL Queued Up 2026 edition (through 2025). "
    "Generation and storage interconnection queues only — "
    "not load interconnection or data-center permit counts. "
    "Do not derive DC proposed/approved/denied tallies from this workbook."
)


def fetch(force: bool = False) -> Path:
    if DEST.exists() and not force:
        print(f"already present: {DEST} ({DEST.stat().st_size} bytes)")
        return DEST
    ok, msg = try_download(
        XLSX_URL,
        DEST,
        source_id="lbnl_queued_up_2026",
        notes=PUB_NOTE,
        license_note="CC BY 4.0 (Lawrence Berkeley National Laboratory / EMP)",
        extra={
            "layer": "G",
            "portal": PORTAL,
            "access_date_pt": "2026-09-16",
            "content_scope": "generation_storage_interconnection_queues",
            "not_in_scope": "data_center_permit_counts",
        },
    )
    print(msg)
    if not ok:
        raise SystemExit(1)
    return DEST


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    fetch(force=args.force)


if __name__ == "__main__":
    main()
