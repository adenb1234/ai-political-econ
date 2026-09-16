"""Geography — Census national places gazetteer + place→county name reference.

Public domain bulk files used for LocalView place GEOID → county FIPS.
"""

from __future__ import annotations

import argparse
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ._download import ROOT, sha256_file, try_download, write_manifest

PT = ZoneInfo("America/Los_Angeles")

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

# Small MIT-licensed town→planning-region table (CT Data Collaborative).
# Needed because 2024 county gazetteer uses COGs, not legacy CT counties.
CT_TOWN_TO_COG_URL = (
    "https://raw.githubusercontent.com/CT-Data-Collaborative/"
    "ct-town-to-planning-region/main/ct-town-to-planning-region.csv"
)
CT_TOWN_TO_COG_DEST = ROOT / "data" / "raw" / "census" / "ct_town_to_planning_region.csv"

# 2020 ANSI place-by-county (COUNTYFP per place). Complements older national_places.txt
# which omits some post-2010 incorporations still present in the 2024 places gazetteer
# (e.g. Semmes AL, Brookhaven GA). Public domain.
PLACE_BY_COUNTY_2020_URL = (
    "https://www2.census.gov/geo/docs/reference/codes2020/"
    "national_place_by_county2020.txt"
)
PLACE_BY_COUNTY_2020_DEST = (
    ROOT / "data" / "raw" / "census" / "national_place_by_county2020.txt"
)


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


def fetch_ct_town_to_cog(force: bool = False) -> Path:
    dest = CT_TOWN_TO_COG_DEST
    extra = {
        "source_id": "census_ct_town_to_planning_region",
        "url": CT_TOWN_TO_COG_URL,
        "path": str(dest.relative_to(ROOT)),
        "status": "downloaded",
        "access_date_pt": datetime.now(PT).date().isoformat(),
        "notes": (
            "CT Data Collaborative town → 2022 planning-region county-equivalents "
            "(Census adopted COGs as county-equivalents in 2022; 2024 gazetteer "
            "no longer lists Fairfield/Litchfield/etc.). MIT license. "
            "Access date recorded in manifest; do not treat as LocalView empirical rows."
        ),
        "license_note": "MIT (CT Data Collaborative); derived from Census TIGER 2022",
        "layer": "geo",
        "upstream": "https://github.com/CT-Data-Collaborative/ct-town-to-planning-region",
    }
    if dest.exists() and not force:
        print(f"already present: {dest}")
        extra.update({"bytes": dest.stat().st_size, "sha256": sha256_file(dest)})
        write_manifest("census_ct_town_to_planning_region", extra)
        return dest
    ok, msg = try_download(
        CT_TOWN_TO_COG_URL,
        dest,
        source_id="census_ct_town_to_planning_region",
        notes=extra["notes"],
        license_note=extra["license_note"],
        extra={
            "layer": "geo",
            "upstream": extra["upstream"],
            "access_date_pt": extra["access_date_pt"],
        },
    )
    print(msg)
    if not ok:
        raise SystemExit(1)
    return dest


def fetch_place_by_county_2020(force: bool = False) -> Path:
    dest = PLACE_BY_COUNTY_2020_DEST
    access_date_pt = datetime.now(PT).date().isoformat()
    payload = {
        "source_id": "census_place_by_county_2020",
        "url": PLACE_BY_COUNTY_2020_URL,
        "path": str(dest.relative_to(ROOT)),
        "status": "downloaded",
        "access_date_pt": access_date_pt,
        "notes": (
            "Census ANSI 2020 national_place_by_county2020.txt — STATEFP+PLACEFP → "
            "COUNTYFP (one row per place×county; multi-county places have multiple rows). "
            "Used as fallback when national_places.txt lacks a 2024 places-gaz GEOID "
            "(Semmes AL / Brookhaven GA). Public domain; do not invent FIPS."
        ),
        "license_note": "US government work / public domain",
        "layer": "geo",
    }
    if dest.exists() and not force:
        print(f"already present: {dest}")
        payload.update({"bytes": dest.stat().st_size, "sha256": sha256_file(dest)})
        # Preserve prior access stamp when unchanged
        meta = ROOT / "data" / "manifests" / "census_place_by_county_2020.json"
        if meta.exists():
            import json

            try:
                prior = json.loads(meta.read_text(encoding="utf-8"))
                if prior.get("sha256") == payload["sha256"] and prior.get("access_date_pt"):
                    payload["access_date_pt"] = prior["access_date_pt"]
            except Exception:  # noqa: BLE001
                pass
        write_manifest("census_place_by_county_2020", payload)
        return dest
    ok, msg = try_download(
        PLACE_BY_COUNTY_2020_URL,
        dest,
        source_id="census_place_by_county_2020",
        notes=payload["notes"],
        license_note=payload["license_note"],
        extra={"layer": "geo", "access_date_pt": access_date_pt},
    )
    print(msg)
    if not ok:
        raise SystemExit(1)
    return dest


def fetch(force: bool = False) -> tuple[Path, Path, Path, Path]:
    return (
        fetch_gaz_places(force=force),
        fetch_national_places(force=force),
        fetch_ct_town_to_cog(force=force),
        fetch_place_by_county_2020(force=force),
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    fetch(force=args.force)


if __name__ == "__main__":
    main()
