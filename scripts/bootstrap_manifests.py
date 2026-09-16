#!/usr/bin/env python3
"""Write manifests for files already on disk (idempotent)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ingest._download import sha256_file, write_manifest  # noqa: E402


def manifest_existing(source_id: str, path: Path, **extra) -> None:
    if not path.exists():
        write_manifest(source_id, {"source_id": source_id, "status": "missing", "path": str(path), **extra})
        return
    write_manifest(
        source_id,
        {
            "source_id": source_id,
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "status": "downloaded",
            **extra,
        },
    )
    print(f"{source_id}: {path} ({path.stat().st_size} bytes)")


def main() -> None:
    manifest_existing(
        "census_gaz_counties_2024",
        ROOT / "data/raw/census/2024_Gaz_counties_national.txt",
        url="https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_counties_national.zip",
        layer="geo",
        license_note="US government work / public domain",
        notes="Unpacked from 2024_Gaz_counties_national.zip",
    )
    manifest_existing(
        "ccc_phase3",
        ROOT / "data/raw/ccc/ccc-phase3-public.csv",
        url="https://dataverse.harvard.edu/api/access/datafile/14226873",
        doi="10.7910/DVN/RI9JFU",
        layer="E",
        license_note="Harvard Dataverse / CCC terms",
        notes="CCC phase 3 public CSV (2025–)",
    )
    manifest_existing(
        "eia_861_2024",
        ROOT / "data/raw/eia/f8612024.zip",
        url="https://www.eia.gov/electricity/data/eia861/zip/f8612024.zip",
        layer="G",
        license_note="US EIA / public domain",
    )
    manifest_existing(
        "localview_codebook",
        ROOT / "data/raw/localview/codebook.md",
        url="https://dataverse.harvard.edu/api/access/datafile/14077924",
        doi="10.7910/DVN/NJTBEM",
        layer="A",
        license_note="Harvard Dataverse / LocalView terms",
    )


if __name__ == "__main__":
    main()
