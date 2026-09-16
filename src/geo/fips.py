"""County FIPS helpers over Census national counties gazetteer.

Default path: data/raw/census/2024_Gaz_counties_national.txt
Download: make fetch-census
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GAZ = ROOT / "data" / "raw" / "census" / "2024_Gaz_counties_national.txt"
GAZ_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2024_Gazetteer/2024_Gaz_counties_national.zip"
)


@dataclass(frozen=True)
class County:
    state: str          # USPS
    fips: str           # 5-digit GEOID
    name: str
    ansicode: str
    land_sqmi: Optional[float] = None
    water_sqmi: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


def normalize_fips(value: str | int | None) -> Optional[str]:
    """Normalize to 5-digit zero-padded FIPS or None."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in {"na", "nan", "none"}:
        return None
    # CCC sometimes stores float-like strings
    if "." in s:
        s = s.split(".", 1)[0]
    if not s.isdigit():
        return None
    return s.zfill(5)


def _f(x: str) -> Optional[float]:
    x = (x or "").strip()
    if not x:
        return None
    try:
        return float(x)
    except ValueError:
        return None


def load_counties(path: Path | None = None) -> list[County]:
    path = path or DEFAULT_GAZ
    if not path.exists():
        raise FileNotFoundError(
            f"Census gazetteer not found at {path}. Run: make fetch-census\nURL: {GAZ_URL}"
        )
    counties: list[County] = []
    # Gazetteer is tab-separated; GEOID is state+county FIPS
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="\t")
        # Normalize field names (Census pads header with spaces)
        for row in reader:
            cleaned = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}
            fips = normalize_fips(cleaned.get("GEOID"))
            state = (cleaned.get("USPS") or "").strip().upper()
            if not fips or not state:
                continue
            counties.append(
                County(
                    state=state,
                    fips=fips,
                    name=cleaned.get("NAME") or "",
                    ansicode=cleaned.get("ANSICODE") or "",
                    land_sqmi=_f(cleaned.get("ALAND_SQMI") or ""),
                    water_sqmi=_f(cleaned.get("AWATER_SQMI") or ""),
                    lat=_f(cleaned.get("INTPTLAT") or ""),
                    lon=_f(cleaned.get("INTPTLONG") or ""),
                )
            )
    return counties


def lookup_fips(
    fips: str,
    counties: Iterable[County] | None = None,
) -> Optional[County]:
    key = normalize_fips(fips)
    if key is None:
        return None
    if counties is None:
        counties = load_counties()
    for c in counties:
        if c.fips == key:
            return c
    return None


def by_state(state: str, counties: Iterable[County] | None = None) -> list[County]:
    st = state.upper()
    if counties is None:
        counties = load_counties()
    return [c for c in counties if c.state == st]


def main() -> None:
    parser = argparse.ArgumentParser(description="Census county FIPS helpers")
    parser.add_argument("--summary", action="store_true", help="Print row counts by state")
    parser.add_argument("--fips", type=str, help="Look up a 5-digit FIPS")
    parser.add_argument("--path", type=str, default=None)
    args = parser.parse_args()
    path = Path(args.path) if args.path else None
    counties = load_counties(path)
    if args.fips:
        c = lookup_fips(args.fips, counties)
        print(c if c else f"not found: {args.fips}")
        return
    if args.summary:
        from collections import Counter

        print(f"counties={len(counties)} path={path or DEFAULT_GAZ}")
        counts = Counter(c.state for c in counties)
        for st, n in sorted(counts.items()):
            print(f"  {st}: {n}")
        return
    print(f"loaded {len(counties)} counties from {path or DEFAULT_GAZ}")


if __name__ == "__main__":
    main()
