"""Geography — Census national counties gazetteer (public domain)."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from ._download import ROOT, try_download

GAZ_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2024_Gazetteer/2024_Gaz_counties_national.zip"
)
ZIP_DEST = ROOT / "data" / "raw" / "census" / "2024_Gaz_counties_national.zip"
TXT_NAME = "2024_Gaz_counties_national.txt"


def fetch(force: bool = False) -> Path:
    txt = ZIP_DEST.with_name(TXT_NAME)
    if txt.exists() and not force:
        print(f"already present: {txt}")
        return txt
    ok, msg = try_download(
        GAZ_URL,
        ZIP_DEST,
        source_id="census_gaz_counties_2024",
        notes="US Census 2024 national counties gazetteer (FIPS GEOID crosswalk).",
        license_note="US government work / public domain",
        extra={"layer": "geo"},
    )
    print(msg)
    if not ok:
        raise SystemExit(1)
    with zipfile.ZipFile(ZIP_DEST) as zf:
        zf.extract(TXT_NAME, path=ZIP_DEST.parent)
    print(f"extracted {txt}")
    return txt


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    fetch(force=args.force)


if __name__ == "__main__":
    main()
