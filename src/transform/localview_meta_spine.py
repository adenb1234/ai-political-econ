"""LocalView meta → spine keys (county_fips + month) v0.

Joins place→county crosswalk v0 onto meta_localview.parquet and derives
month (YYYY-MM) from meeting_date. Does not invent FIPS or event rows.
Does not download transcript tarballs.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from src.ingest._download import ROOT

META_PATH = ROOT / "data" / "raw" / "localview" / "meta_localview.parquet"
CROSSWALK_PATH = (
    ROOT / "data" / "processed" / "crosswalks" / "localview_place_to_county_v0.csv"
)
OUT_PARQUET = ROOT / "data" / "processed" / "localview" / "meta_spine_v0.parquet"
OUT_QA = ROOT / "data" / "processed" / "qa" / "localview_meta_spine_v0_qa.json"

SPINE_VERSION = "localview_meta_spine_v0"
PT = ZoneInfo("America/Los_Angeles")

# Meta columns kept for audit / downstream joins.
META_KEEP = [
    "id",
    "meeting_date",
    "st_fips",
    "place_names",
    "multiple_cities",
    "predicted_st_fips",
    "government_type",
    "channel_id",
]

CROSSWALK_KEEP = [
    "county_fips",
    "state",
    "county_name",
    "all_county_fips",
    "confidence",
    "method",
]

JOIN_KEYS_META = ["st_fips", "place_names", "multiple_cities", "predicted_st_fips"]
JOIN_KEYS_XW = ["st_fips_raw", "place_names", "multiple_cities", "predicted_st_fips"]


def _access_date_pt() -> str:
    return datetime.now(PT).strftime("%Y-%m-%d")


def _normalize_key_frame(df: Any, *, st_col: str) -> Any:
    """Align join-key dtypes/string forms with crosswalk build conventions."""
    out = df.copy()
    out[st_col] = out[st_col].fillna("").astype(str)
    out["place_names"] = out["place_names"].fillna("").astype(str)
    out["predicted_st_fips"] = out["predicted_st_fips"].fillna("").astype(str)
    # Crosswalk build used int(multiple_cities or 0)
    out["multiple_cities"] = (
        out["multiple_cities"].fillna(0).astype("int64")
    )
    return out


def _parse_month(series: Any) -> tuple[Any, int]:
    """Return (month YYYY-MM series, parse_fail_count).

    Null / NaT / unparseable values become empty string and count as failures.
    """
    import pandas as pd

    raw = series
    # Already datetime64 from parquet in the common case.
    if not pd.api.types.is_datetime64_any_dtype(raw):
        parsed = pd.to_datetime(raw, errors="coerce")
    else:
        parsed = raw

    null_mask = parsed.isna()
    # Also treat all-null object leftovers as fails (already in null_mask after coerce).
    month = parsed.dt.strftime("%Y-%m")
    month = month.where(~null_mask, other="")
    # Empty string for any remaining NA from strftime edge cases
    month = month.fillna("")
    parse_fail = int((month == "").sum())
    return month, parse_fail


def build_spine(
    meta_path: Path | None = None,
    crosswalk_path: Path | None = None,
) -> tuple[Any, dict]:
    meta_path = meta_path or META_PATH
    crosswalk_path = crosswalk_path or CROSSWALK_PATH

    if not meta_path.exists():
        raise FileNotFoundError(f"LocalView meta missing: {meta_path}")
    if not crosswalk_path.exists():
        raise FileNotFoundError(
            f"Crosswalk missing: {crosswalk_path}. Run: make crosswalk-localview"
        )

    try:
        import pandas as pd
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "pandas+pyarrow required. Use: /workspace/ai-backlash-tracker/.venv"
        ) from exc

    meta = pq.read_table(meta_path, columns=META_KEEP).to_pandas()
    xw = pd.read_csv(
        crosswalk_path,
        dtype={
            "st_fips_raw": str,
            "place_names": str,
            "predicted_st_fips": str,
            "county_fips": str,
            "state": str,
            "county_name": str,
            "all_county_fips": str,
            "confidence": str,
            "method": str,
            "notes": str,
        },
        keep_default_na=False,
        na_filter=False,
    )
    # multiple_cities / n_meta_rows may still need numeric cast
    xw["multiple_cities"] = pd.to_numeric(xw["multiple_cities"], errors="coerce").fillna(0).astype("int64")

    meta = _normalize_key_frame(meta, st_col="st_fips")
    xw_keys = xw[JOIN_KEYS_XW + CROSSWALK_KEEP].copy()
    xw_keys = xw_keys.rename(columns={"st_fips_raw": "st_fips"})

    n_meta = int(len(meta))
    n_xw = int(len(xw_keys))

    merged = meta.merge(
        xw_keys,
        on=JOIN_KEYS_META,
        how="left",
        validate="many_to_one",
    )

    if len(merged) != n_meta:
        raise RuntimeError(
            f"Join changed row count: meta={n_meta} merged={len(merged)} "
            "(expected many_to_one place-key join)"
        )

    month, parse_fail = _parse_month(merged["meeting_date"])
    merged["month"] = month

    # Fill crosswalk missings for unmatched keys (should be rare if crosswalk covers all keys)
    for col in CROSSWALK_KEEP:
        if col not in merged.columns:
            merged[col] = ""
        merged[col] = merged[col].fillna("").astype(str)

    has_county = merged["county_fips"].astype(str).str.len() > 0
    has_month = merged["month"].astype(str).str.len() > 0
    spine_ready = has_county & has_month

    # Output column order
    out_cols = [
        "id",
        "meeting_date",
        "month",
        "st_fips",
        "place_names",
        "multiple_cities",
        "predicted_st_fips",
        "government_type",
        "channel_id",
        "county_fips",
        "state",
        "county_name",
        "all_county_fips",
        "confidence",
        "method",
    ]
    out_df = merged[out_cols].copy()

    # meeting_date as ISO date string for stable parquet/CSV consumers
    if pd.api.types.is_datetime64_any_dtype(out_df["meeting_date"]):
        out_df["meeting_date"] = out_df["meeting_date"].dt.strftime("%Y-%m-%d")
        out_df["meeting_date"] = out_df["meeting_date"].fillna("")

    conf_counts = (
        out_df.loc[has_county, "confidence"].value_counts().to_dict()
        if has_county.any()
        else {}
    )
    # Also overall confidence including unmatched (empty → "unjoined")
    conf_all = out_df["confidence"].replace("", "unjoined").value_counts().to_dict()

    # Row-level geo buckets aligned with crosswalk confidence policy:
    # matched = non-empty county_fips; ambiguous = empty county_fips but
    # candidates in all_county_fips; unmatched = neither.
    has_all = out_df["all_county_fips"].astype(str).str.len() > 0
    rows_matched = int(has_county.sum())
    rows_ambiguous = int((~has_county & has_all).sum())
    rows_unmatched = int((~has_county & ~has_all).sum())
    month_ok = int(has_month.sum())

    qa = {
        "spine_version": SPINE_VERSION,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "access_date_pt": _access_date_pt(),
        "meta_path": str(meta_path.relative_to(ROOT)),
        "crosswalk_path": str(crosswalk_path.relative_to(ROOT)),
        "crosswalk_version": "localview_place_to_county_v0",
        "join_keys": JOIN_KEYS_META,
        "meta_rows": n_meta,
        "crosswalk_keys": n_xw,
        "rows_matched_county": rows_matched,
        "rows_ambiguous": rows_ambiguous,
        "rows_unmatched": rows_unmatched,
        "rows_with_county_fips": rows_matched,
        "rows_with_county_fips_share": round(float(has_county.mean()), 4) if n_meta else 0.0,
        "month_parse_success": month_ok,
        "month_parse_fail": parse_fail,
        "rows_with_month": month_ok,
        "rows_with_month_share": round(float(has_month.mean()), 4) if n_meta else 0.0,
        "meeting_date_parse_fail": parse_fail,
        "meeting_date_parse_fail_share": round(parse_fail / n_meta, 4) if n_meta else 0.0,
        "spine_ready_rows": int(spine_ready.sum()),
        "spine_ready_share": round(float(spine_ready.mean()), 4) if n_meta else 0.0,
        "rows_unjoined_to_crosswalk": int((out_df["method"] == "").sum()),
        "confidence_counts_among_county_matched": {str(k): int(v) for k, v in conf_counts.items()},
        "confidence_counts_all_rows": {str(k): int(v) for k, v in conf_all.items()},
        "output_parquet": str(OUT_PARQUET.relative_to(ROOT)),
        "notes": (
            "Spine-ready = non-empty county_fips AND non-empty month (YYYY-MM). "
            "county_fips comes only from crosswalk v0 (no invented FIPS). "
            "meeting_date null/unparseable → empty month and counted in parse_fail. "
            "No transcript tarballs; no empirical event rows invented."
        ),
        "license_bias": (
            "LocalView / Harvard Dataverse terms; cite DOI 10.7910/DVN/NJTBEM. "
            "Meeting-recording places skew larger / richer / more urban."
        ),
    }

    # Attach table for write (keep as pandas; writer converts)
    out_df.attrs["qa"] = qa  # type: ignore[attr-defined]
    return out_df, qa


def write_outputs(
    df: Any,
    qa: dict,
    out_parquet: Path | None = None,
    out_qa: Path | None = None,
) -> tuple[Path, Path]:
    import pyarrow as pa
    import pyarrow.parquet as pq

    out_parquet = out_parquet or OUT_PARQUET
    out_qa = out_qa or OUT_QA
    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    out_qa.parent.mkdir(parents=True, exist_ok=True)

    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, out_parquet, compression="zstd")
    out_qa.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    return out_parquet, out_qa


def main() -> None:
    p = argparse.ArgumentParser(
        description="Join LocalView meta to county crosswalk + derive month spine v0"
    )
    p.add_argument("--meta", type=str, default=None)
    p.add_argument("--crosswalk", type=str, default=None)
    args = p.parse_args()
    meta = Path(args.meta) if args.meta else None
    xw = Path(args.crosswalk) if args.crosswalk else None
    df, qa = build_spine(meta, xw)
    pq_path, qa_path = write_outputs(df, qa)
    print(f"wrote {pq_path} ({qa['meta_rows']} rows)")
    print(f"wrote {qa_path}")
    print(
        "QA:",
        f"meta={qa['meta_rows']}",
        f"with_county={qa['rows_with_county_fips']} ({qa['rows_with_county_fips_share']})",
        f"with_month={qa['rows_with_month']} ({qa['rows_with_month_share']})",
        f"spine_ready={qa['spine_ready_rows']} ({qa['spine_ready_share']})",
        f"parse_fail={qa['meeting_date_parse_fail']}",
    )


if __name__ == "__main__":
    main()
