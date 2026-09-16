"""Geography — Census national places gazetteer + place→county name reference.

Public domain bulk files used for LocalView place GEOID → county FIPS.
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from ._download import ROOT, sha256_file, try_download, write_manifest

GAZ_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2024_Gazetteer/2024_Gaz_place_national.zip"
)
ZIP_DEST = ROOT / "data" / "raw" / "census" / "2024_Gaz_place_national.zip"
TXT_NAME = "2024_Gaz_place_national.txt"

# Older Census reference file: STATEFP|PLACEFP|…|COUNTY (county *names*, possibly multi).
# Complements the gazetteer (which has no county column).
NATIONAL_PLACES_URL = (
    "https://www2.census.gov/geo/docs/reference/codes/files/national_places.txt"
)
NATIONAL_PLACES_DEST = ROOT / "data" / "raw" / "census" / "national_places.txt"


def _write_gaz_manifest(txt: Path) -> None:
    write_manifest(
        "census_gaz_places_2024",
        {
            "source_id": "census_gaz_places_2024",
            "url": GAZ_URL,
            "path": str(txt.relative_to(ROOT)),
            "zip_path": str(ZIP_DEST.relative_to(ROOT)),
            "bytes": txt.stat().st_size,
            "zip_bytes": ZIP_DEST.stat().st_size if ZIP_DEST.exists() else None,
            "sha256": sha256_file(txt),
            "status": "downloaded",
            "notes": "Unpacked from 2024_Gaz_place_national.zip; place GEOID validation (no county column).",
            "license_note": "US government work / public domain",
            "layer": "geo",
        },
    )


def fetch_gaz_places(force: bool = False) -> Path:
    txt = ZIP_DEST.with_name(TXT_NAME)
    if txt.exists() and not force:
        print(f"already present: {txt}")
        _write_gaz_manifest(txt)
        return txt
    ok, msg = try_download(
        GAZ_URL,
        ZIP_DEST,
        source_id="census_gaz_places_2024",
        notes="US Census 2024 national places gazetteer (7-digit state+place GEOID).",
        license_note="US government work / public domain",
        extra={"layer": "geo"},
    )
    print(msg)
    if not ok:
        raise SystemExit(1)
    with zipfile.ZipFile(ZIP_DEST) as zf:
        zf.extract(TXT_NAME, path=ZIP_DEST.parent)
    _write_gaz_manifest(txt)
    print(f"extracted {txt}")
    return txt


def fetch_national_places(force: bool = False) -> Path:
    dest = NATIONAL_PLACES_DEST
    if dest.exists() and not force:
        print(f"already present: {dest}")
        write_manifest(
            "census_national_places",
            {
                "source_id": "census_national_places",
                "url": NATIONAL_PLACES_URL,
                "path": str(dest.relative_to(ROOT)),
                "bytes": dest.stat().st_size,
                "sha256": sha256_file(dest),
                "status": "downloaded",
                "notes": (
                    "Census national_places.txt — place GEOID to county name(s). "
                    "Multi-county places list comma-separated county names; do not invent a single FIPS."
                ),
                "license_note": "US government work / public domain",
                "layer": "geo",
            },
        )
        return dest
    ok, msg = try_download(
        NATIONAL_PLACES_URL,
        dest,
        source_id="census_national_places",
        notes=(
            "Census national_places.txt — place GEOID to county name(s). "
            "Multi-county places list comma-separated county names; do not invent a single FIPS."
        ),
        license_note="US government work / public domain",
        extra={"layer": "geo"},
    )
    print(msg)
    if not ok:
        raise SystemExit(1)
    return dest


def fetch(force: bool = False) -> tuple[Path, Path]:
    return fetch_gaz_places(force=force), fetch_national_places(force=force)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    fetch(force=args.force)


if __name__ == "__main__":
    main()
