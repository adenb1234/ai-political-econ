"""Layer A — LocalView public meetings (Harvard Dataverse).

Dataset DOI: 10.7910/DVN/NJTBEM
Codebook (small, free): datafile 14077924
Meta parquet (~35 MB): datafile 14233652 — fetch with --include-meta
  (also builds place→county crosswalk + meta spine: county_fips / state / month).
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
                    "Geo: --include-meta builds place→county crosswalk v0 + meta spine v0 "
                    "(county_fips / state / month). Or: make crosswalk-localview && make spine-localview."
                ),
                "meta_path": str(meta_path.relative_to(ROOT)),
                "meta_bytes": meta_path.stat().st_size,
                "meta_sha256": dig,
                "meta_status": "downloaded",
                "meta_access_date_pt": prior_access_pt or stamps["access_date_pt"],
                "meta_accessed_at_utc": prior_access_utc or stamps["accessed_at_utc"],
                "geo_crosswalk": "data/processed/crosswalks/localview_place_to_county_v0.csv",
                "geo_crosswalk_qa": "data/processed/qa/localview_place_to_county_v0_qa.json",
                "meta_spine": "data/processed/localview/meta_spine_v0.parquet",
                "meta_spine_qa": "data/processed/qa/localview_meta_spine_v0_qa.json",
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


def _ensure_meta_geo(*, rebuild_crosswalk: bool = False) -> None:
    """Build place→county crosswalk (if needed) + meta spine under data/processed/.

    Requires Census gazetteers on disk (make fetch-census / fetch-census-places).
    Does not invent FIPS; does not download transcript tarballs.
    """
    from src.transform.localview_geo import (
        OUT_CSV as CROSSWALK_CSV,
        build_crosswalk,
        write_outputs as write_crosswalk,
    )
    from src.transform.localview_meta_spine import build_spine, write_outputs as write_spine

    if rebuild_crosswalk or not CROSSWALK_CSV.exists():
        print("geo: building place→county crosswalk v0 …")
        rows, qa = build_crosswalk(DEST_META)
        csv_path, qa_path = write_crosswalk(rows, qa)
        print(
            f"geo: wrote {csv_path.relative_to(ROOT)} ({qa['unique_place_keys']} keys; "
            f"meta_matched_share={qa['meta_rows_matched_share']})"
        )
        print(f"geo: wrote {qa_path.relative_to(ROOT)}")
    else:
        print(f"geo: crosswalk already present: {CROSSWALK_CSV.relative_to(ROOT)}")

    print("geo: building meta spine v0 (county_fips / state / month) …")
    df, spine_qa = build_spine(DEST_META, CROSSWALK_CSV)
    pq_path, spine_qa_path = write_spine(df, spine_qa)
    print(
        f"geo: wrote {pq_path.relative_to(ROOT)} "
        f"(spine_ready={spine_qa['spine_ready_rows']} / {spine_qa['meta_rows']}; "
        f"share={spine_qa['spine_ready_share']})"
    )
    print(f"geo: wrote {spine_qa_path.relative_to(ROOT)}")


def fetch(
    force: bool = False,
    include_meta: bool = False,
    *,
    skip_geo: bool = False,
    rebuild_crosswalk: bool = False,
) -> None:
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

        if meta_ok_path is not None and not skip_geo:
            try:
                _ensure_meta_geo(rebuild_crosswalk=rebuild_crosswalk or force)
            except FileNotFoundError as exc:
                print(f"geo: skipped — missing Census asset ({exc})")
                print("geo: run: make fetch-census && make fetch-census-places")
            except Exception as exc:  # noqa: BLE001
                print(f"geo: failed ({exc})")
                raise SystemExit(1) from exc
    elif DEST_META.exists():
        meta_ok_path = DEST_META

    _write_localview_manifest(meta_path=meta_ok_path)


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Fetch LocalView codebook (+ optional meta). "
            "With --include-meta, also build county_fips/state/month spine outputs."
        )
    )
    p.add_argument("--force", action="store_true", help="Re-download and rebuild crosswalk")
    p.add_argument(
        "--include-meta",
        action="store_true",
        help="Fetch ~35MB meta parquet and build geo-keyed spine outputs",
    )
    p.add_argument(
        "--skip-geo",
        action="store_true",
        help="With --include-meta, only fetch meta (skip crosswalk/spine)",
    )
    p.add_argument(
        "--rebuild-crosswalk",
        action="store_true",
        help="Force rebuild place→county crosswalk even if CSV exists",
    )
    args = p.parse_args()
    fetch(
        force=args.force,
        include_meta=args.include_meta,
        skip_geo=args.skip_geo,
        rebuild_crosswalk=args.rebuild_crosswalk,
    )


if __name__ == "__main__":
    main()
