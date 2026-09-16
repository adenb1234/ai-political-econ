"""Layer G — EIA Form 861 annual detailed data (public domain, no key)."""

from __future__ import annotations

import argparse
from pathlib import Path

from ._download import ROOT, try_download

# Current complete year on EIA portal at scaffold time
EIA_861_2024_URL = "https://www.eia.gov/electricity/data/eia861/zip/f8612024.zip"
DEST = ROOT / "data" / "raw" / "eia" / "f8612024.zip"
PORTAL = "https://www.eia.gov/electricity/data/eia861/"


def fetch(force: bool = False) -> Path:
    if DEST.exists() and not force:
        print(f"already present: {DEST} ({DEST.stat().st_size} bytes)")
        return DEST
    ok, msg = try_download(
        EIA_861_2024_URL,
        DEST,
        source_id="eia_861_2024",
        notes=f"EIA-861 2024 annual zip. Portal: {PORTAL}. Denominator / utility context for layer G.",
        license_note="US EIA / public domain",
        extra={"layer": "G", "portal": PORTAL},
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
