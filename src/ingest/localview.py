"""Layer A — LocalView public meetings (Harvard Dataverse).

Dataset DOI: 10.7910/DVN/NJTBEM
Codebook (small, free): datafile 14077924
Meta parquet (~35 MB): datafile 14233652 — fetch with --include-meta
Transcripts: multi-GB tarballs — download on demand, not mirrored by default.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from ._download import ROOT, sha256_file, try_download, write_manifest

DOI = "10.7910/DVN/NJTBEM"
CODEBOOK_URL = "https://dataverse.harvard.edu/api/access/datafile/14077924"
META_URL = "https://dataverse.harvard.edu/api/access/datafile/14233652"  # ~35 MB parquet
DEST_CODEBOOK = ROOT / "data" / "raw" / "localview" / "codebook.md"
DEST_META = ROOT / "data" / "raw" / "localview" / "meta_localview.parquet"
DATASET_PAGE = f"https://doi.org/{DOI}"
PT = ZoneInfo("America/Los_Angeles")


def _access_stamps() -> dict[str, str]:
    now_utc = datetime.now(timezone.utc)
    return {
        "access_date_pt": now_utc.astimezone(PT).date().isoformat(),
        "accessed_at_utc": now_utc.isoformat(),
    }


def _write_localview_manifest(*, meta_path: Path | None) -> None:
    payload: dict = {
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
    }
    if meta_path is not None and meta_path.exists():
        dig = sha256_file(meta_path)
        stamps = _access_stamps()
        # Prefer prior access stamps from localview_meta.json when file unchanged.
        meta_manifest = ROOT / "data" / "manifests" / "localview_meta.json"
        prior_access_pt = None
        prior_access_utc = None
        if meta_manifest.exists():
            import json

            try:
                prior = json.loads(meta_manifest.read_text(encoding="utf-8"))
                if prior.get("sha256") == dig:
                    prior_access_pt = prior.get("access_date_pt")
                    prior_access_utc = prior.get("accessed_at_utc")
            except Exception:  # noqa: BLE001
                pass
        payload.update(
            {
                "status": "meta_downloaded",
                "notes": (
                    "Full transcripts intentionally not auto-fetched (≈5+ GB); "
                    "transcript tarballs remain excluded. Metadata parquet downloaded. "
                    "Geo: place→county FIPS crosswalk v0 at "
                    "data/processed/crosswalks/localview_place_to_county_v0.csv "
                    "(make crosswalk-localview)."
                ),
                "meta_path": str(meta_path.relative_to(ROOT)),
                "meta_bytes": meta_path.stat().st_size,
                "meta_sha256": dig,
                "meta_status": "downloaded",
                "meta_access_date_pt": prior_access_pt or stamps["access_date_pt"],
                "meta_accessed_at_utc": prior_access_utc or stamps["accessed_at_utc"],
                "geo_crosswalk": "data/processed/crosswalks/localview_place_to_county_v0.csv",
                "geo_crosswalk_qa": "data/processed/qa/localview_place_to_county_v0_qa.json",
            }
        )
    else:
        payload.update(
            {
                "status": "codebook_downloaded",
                "notes": (
                    "Full transcripts intentionally not auto-fetched (≈5+ GB). "
                    "Use Dataverse API access/datafile/{id} when ready. "
                    "Geo: st_fips / place_names per codebook — county crosswalk TBD."
                ),
            }
        )
    write_manifest("localview", payload)


def _record_meta_manifest(dest: Path, *, freshly_downloaded: bool) -> None:
    dig = sha256_file(dest)
    stamps = _access_stamps()
    meta_manifest = ROOT / "data" / "manifests" / "localview_meta.json"
    access_date_pt = stamps["access_date_pt"]
    accessed_at_utc = stamps["accessed_at_utc"]
    if not freshly_downloaded and meta_manifest.exists():
        import json

        try:
            prior = json.loads(meta_manifest.read_text(encoding="utf-8"))
            if prior.get("sha256") == dig:
                access_date_pt = prior.get("access_date_pt") or access_date_pt
                accessed_at_utc = prior.get("accessed_at_utc") or accessed_at_utc
        except Exception:  # noqa: BLE001
            pass
    write_manifest(
        "localview_meta",
        {
            "source_id": "localview_meta",
            "url": META_URL,
            "path": str(dest.relative_to(ROOT)),
            "bytes": dest.stat().st_size,
            "sha256": dig,
            "status": "downloaded",
            "notes": "LocalView metadata parquet (~35 MB).",
            "license_note": "Harvard Dataverse / LocalView terms",
            "doi": DOI,
            "layer": "A",
            "access_date_pt": access_date_pt,
            "accessed_at_utc": accessed_at_utc,
        },
    )


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

    meta_ok_path: Path | None = None
    if include_meta:
        if DEST_META.exists() and not force:
            print(f"meta already present: {DEST_META} ({DEST_META.stat().st_size} bytes)")
            _record_meta_manifest(DEST_META, freshly_downloaded=False)
            meta_ok_path = DEST_META
            print("meta: skipped re-download (use --force to refresh)")
        else:
            ok, msg = try_download(
                META_URL,
                DEST_META,
                source_id="localview_meta",
                notes="LocalView metadata parquet (~35 MB).",
                license_note="Harvard Dataverse / LocalView terms",
                extra={"doi": DOI, "layer": "A", **_access_stamps()},
            )
            print("meta:", msg)
            if ok:
                _record_meta_manifest(DEST_META, freshly_downloaded=True)
                meta_ok_path = DEST_META
            else:
                raise SystemExit(1)
    elif DEST_META.exists():
        meta_ok_path = DEST_META

    _write_localview_manifest(meta_path=meta_ok_path)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    p.add_argument("--include-meta", action="store_true", help="Also fetch ~35MB meta parquet")
    args = p.parse_args()
    fetch(force=args.force, include_meta=args.include_meta)


if __name__ == "__main__":
    main()
