"""Layer E — Crowd Counting Consortium (free Dataverse CSV).

Public phase-3 file (2025–):
  DOI 10.7910/DVN/RI9JFU
  https://dataverse.harvard.edu/api/access/datafile/14226873
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ._download import ROOT, try_download

CCC_PHASE3_URL = "https://dataverse.harvard.edu/api/access/datafile/14226873"
CCC_DOI = "10.7910/DVN/RI9JFU"
DEST = ROOT / "data" / "raw" / "ccc" / "ccc-phase3-public.csv"


def fetch(force: bool = False) -> Path:
    if DEST.exists() and not force:
        print(f"already present: {DEST} ({DEST.stat().st_size} bytes)")
        return DEST
    ok, msg = try_download(
        CCC_PHASE3_URL,
        DEST,
        source_id="ccc_phase3",
        notes="Crowd Counting Consortium US protest events phase 3 (2025–). Monthly Dataverse updates.",
        license_note="Harvard Dataverse / CCC terms; cite DOI 10.7910/DVN/RI9JFU",
        extra={"doi": CCC_DOI, "layer": "E"},
    )
    print(msg)
    if not ok:
        raise SystemExit(1)
    return DEST


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch CCC phase-3 public CSV")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    fetch(force=args.force)


if __name__ == "__main__":
    main()
