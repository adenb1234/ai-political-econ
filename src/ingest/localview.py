"""Layer A — LocalView public meetings (Harvard Dataverse).

Dataset DOI: 10.7910/DVN/NJTBEM
Codebook (small, free): datafile 14077924
Transcripts: multi-GB tarballs — download on demand, not mirrored by default.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ._download import ROOT, try_download, write_manifest

DOI = "10.7910/DVN/NJTBEM"
CODEBOOK_URL = "https://dataverse.harvard.edu/api/access/datafile/14077924"
META_URL = "https://dataverse.harvard.edu/api/access/datafile/14233652"  # ~35 MB parquet
DEST_CODEBOOK = ROOT / "data" / "raw" / "localview" / "codebook.md"
DATASET_PAGE = f"https://doi.org/{DOI}"


def fetch(force: bool = False, include_meta: bool = False) -> None:
    if DEST_CODEBOOK.exists() and not force:
        print(f"codebook already present: {DEST_CODEBOOK}")
    else:
        ok, msg = try_download(
            CODEBOOK_URL,
            DEST_CODEBOOK,
            source_id="localview_codebook",
            notes="LocalView codebook (variables + example code).",
            license_note="Harvard Dataverse / LocalView terms; cite DOI 10.7910/DVN/NJTBEM",
            extra={"doi": DOI, "layer": "A"},
        )
        print("codebook:", msg)
        if not ok:
            raise SystemExit(1)

    write_manifest(
        "localview",
        {
            "source_id": "localview",
            "layer": "A",
            "doi": DOI,
            "dataset_page": DATASET_PAGE,
            "codebook_path": str(DEST_CODEBOOK.relative_to(ROOT)),
            "meta_parquet_url": META_URL,
            "transcript_parts": [
                {"datafile_id": 14233653, "approx_bytes": 2135971840, "name": "transcripts_localview_part1.tar"},
                {"datafile_id": 14233654, "approx_bytes": 2136422400, "name": "transcripts_localview_part2.tar"},
                {"datafile_id": 14233655, "approx_bytes": 1038776320, "name": "transcripts_localview_part3.tar"},
            ],
            "status": "codebook_downloaded",
            "notes": (
                "Full transcripts intentionally not auto-fetched (≈5+ GB). "
                "Use Dataverse API access/datafile/{id} when ready. "
                "Geo: st_fips / place_names per codebook — county crosswalk TBD."
            ),
        },
    )

    if include_meta:
        dest = ROOT / "data" / "raw" / "localview" / "meta_localview.parquet"
        ok, msg = try_download(
            META_URL,
            dest,
            source_id="localview_meta",
            notes="LocalView metadata parquet (~35 MB).",
            license_note="Harvard Dataverse / LocalView terms",
            extra={"doi": DOI, "layer": "A"},
        )
        print("meta:", msg)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    p.add_argument("--include-meta", action="store_true", help="Also fetch ~35MB meta parquet")
    args = p.parse_args()
    fetch(force=args.force, include_meta=args.include_meta)


if __name__ == "__main__":
    main()
