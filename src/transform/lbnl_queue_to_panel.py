"""LBNL Queued Up → layer-G panel-ish counts (generation/storage interconnection).

Reads sheet ``03. Complete Queue Data`` from the Queued Up 2026 workbook already
on disk. Maps rows to ``state`` + best-effort ``county_fips`` (from upstream
``fips_code``) and ``month`` (YYYY-MM from ``q_date`` = interconnection request).

IMPORTANT
---------
These counts are **generation / storage interconnection queue activity**.
They are **NOT** data-center permit proposed/approved/denied tallies.
Do not populate panel ``n_projects_*`` DC fields from this transform.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from openpyxl import load_workbook

from src.geo.fips import load_counties, normalize_fips

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW = ROOT / "data" / "raw" / "lbnl" / "LBNL_Ix_Queue_Data_File_thru2025.xlsx"
SHEET_NAME = "03. Complete Queue Data"

OUT_PANEL = ROOT / "data" / "processed" / "panel" / "lbnl_ix_queue_activity_v0.csv"
OUT_PANEL_STATE = ROOT / "data" / "processed" / "panel" / "lbnl_ix_queue_activity_state_month_v0.csv"
OUT_SAMPLE = ROOT / "data" / "processed" / "panel" / "lbnl_ix_queue_activity_v0_sample.csv"
OUT_QA = ROOT / "data" / "processed" / "qa" / "lbnl_ix_queue_activity_v0_qa.json"

TRANSFORM_VERSION = "lbnl_ix_queue_v0"
METRIC_LABEL = "generation_storage_interconnection_queue_activity"
NOT_DC_PERMITS = True
SAMPLE_N = 200

# Prefer q_date (request entered the queue) for "queue activity" month.
DATE_FIELDS_PRIORITY = ("q_date", "ia_date", "on_date", "wd_date", "prop_date")


def _parse_month(value: Any) -> Optional[str]:
    """Return YYYY-MM from datetime/date/string, else None."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return f"{value.year:04d}-{value.month:02d}"
    if isinstance(value, date):
        return f"{value.year:04d}-{value.month:02d}"
    s = str(value).strip()
    if not s or s.lower() in {"na", "nan", "none", "nat"}:
        return None
    # Excel serial sometimes arrives as int/float
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            # openpyxl data_only usually gives datetime; skip serial guess
            return None
        except Exception:
            return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s[:19], fmt)
            return f"{dt.year:04d}-{dt.month:02d}"
        except ValueError:
            continue
    if len(s) >= 7 and s[4] == "-" and s[:4].isdigit() and s[5:7].isdigit():
        return s[:7]
    return None


def _norm_state(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip().upper()
    if len(s) == 2 and s.isalpha():
        return s
    return None


def _mw(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_queue_rows(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    wb = load_workbook(path, read_only=True, data_only=True)
    if SHEET_NAME not in wb.sheetnames:
        wb.close()
        raise ValueError(f"Sheet {SHEET_NAME!r} not in {path.name}: {wb.sheetnames}")
    ws = wb[SHEET_NAME]
    it = ws.iter_rows(values_only=True)
    header: Optional[list[str]] = None
    for row in it:
        if row and row[0] == "q_id":
            header = [str(c) if c is not None else f"col_{i}" for i, c in enumerate(row)]
            break
    if not header:
        wb.close()
        raise ValueError(f"Could not find header row (q_id) in {SHEET_NAME}")

    rows: list[dict[str, Any]] = []
    for row in it:
        if not row or row[0] is None:
            continue
        rec = {header[i]: row[i] if i < len(row) else None for i in range(len(header))}
        rows.append(rec)
    wb.close()
    return header, rows


def transform(
    raw_path: Path = DEFAULT_RAW,
    *,
    panel_csv: Path = OUT_PANEL,
    panel_state_csv: Path = OUT_PANEL_STATE,
    sample_csv: Path = OUT_SAMPLE,
    qa_json: Path = OUT_QA,
    sample_n: int = SAMPLE_N,
) -> dict[str, Any]:
    if not raw_path.exists():
        raise FileNotFoundError(
            f"LBNL Queued Up XLSX not found at {raw_path}. Run: make fetch-lbnl"
        )

    generated_at = datetime.now(timezone.utc)
    header, raw_rows = _read_queue_rows(raw_path)

    # Optional FIPS validation against Census gazetteer (presence check).
    known_fips: set[str] = set()
    try:
        known_fips = {c.fips for c in load_counties()}
    except FileNotFoundError:
        known_fips = set()

    qa_exceptions: list[dict[str, Any]] = []
    by_status: Counter[str] = Counter()
    by_type: Counter[str] = Counter()
    by_state: Counter[str] = Counter()

    n_total = 0
    n_fips = 0
    n_state_only = 0
    n_no_geo = 0
    n_month_ok = 0
    n_month_fail = 0
    n_fips_not_in_gaz = 0
    n_mw_ok = 0

    # Panel: county_fips × month (FIPS rows only)
    county_month: dict[tuple[str, str, str], dict[str, Any]] = {}
    # State × month (all rows with state + month, including those with FIPS)
    state_month: dict[tuple[str, str], dict[str, Any]] = {}

    sample_rows: list[dict[str, Any]] = []

    for rec in raw_rows:
        n_total += 1
        status = str(rec.get("q_status") or "").strip().lower() or "unknown"
        type_clean = str(rec.get("type_clean") or "").strip() or "unknown"
        by_status[status] += 1
        by_type[type_clean] += 1

        state = _norm_state(rec.get("state"))
        if state:
            by_state[state] += 1

        fips = normalize_fips(rec.get("fips_code"))
        if fips and known_fips and fips not in known_fips:
            n_fips_not_in_gaz += 1
            # Keep upstream FIPS; log once-style exception (cap later)
            if len(qa_exceptions) < 500:
                qa_exceptions.append(
                    {
                        "kind": "fips_not_in_gazetteer",
                        "q_id": rec.get("q_id"),
                        "entity": rec.get("entity"),
                        "state": state,
                        "county": rec.get("county"),
                        "fips_code": fips,
                    }
                )

        month = None
        month_source = None
        for field in DATE_FIELDS_PRIORITY:
            month = _parse_month(rec.get(field))
            if month:
                month_source = field
                break
        if month:
            n_month_ok += 1
        else:
            n_month_fail += 1
            if len(qa_exceptions) < 500:
                qa_exceptions.append(
                    {
                        "kind": "month_unparseable",
                        "q_id": rec.get("q_id"),
                        "entity": rec.get("entity"),
                        "state": state,
                        "q_date": str(rec.get("q_date")),
                    }
                )

        geo_level = None
        if fips and state:
            n_fips += 1
            geo_level = "county_fips"
        elif state:
            n_state_only += 1
            geo_level = "state_only"
            if len(qa_exceptions) < 500:
                qa_exceptions.append(
                    {
                        "kind": "state_only_missing_fips",
                        "q_id": rec.get("q_id"),
                        "entity": rec.get("entity"),
                        "state": state,
                        "county": rec.get("county"),
                        "fips_raw": rec.get("fips_code"),
                    }
                )
        else:
            n_no_geo += 1
            if len(qa_exceptions) < 500:
                qa_exceptions.append(
                    {
                        "kind": "no_geo",
                        "q_id": rec.get("q_id"),
                        "entity": rec.get("entity"),
                        "county": rec.get("county"),
                        "state_raw": rec.get("state"),
                    }
                )

        mw1 = _mw(rec.get("mw_1"))
        if mw1 is not None:
            n_mw_ok += 1

        if len(sample_rows) < sample_n:
            sample_rows.append(
                {
                    "q_id": rec.get("q_id"),
                    "entity": rec.get("entity"),
                    "q_status": status,
                    "type_clean": type_clean,
                    "state": state or "",
                    "county": rec.get("county") or "",
                    "county_fips": fips or "",
                    "geo_level": geo_level or "",
                    "month": month or "",
                    "month_source": month_source or "",
                    "mw_1": "" if mw1 is None else mw1,
                    "region": rec.get("region") or "",
                    "metric_label": METRIC_LABEL,
                    "not_data_center_permits": "true",
                }
            )

        if month and fips and state:
            key = (fips, state, month)
            agg = county_month.get(key)
            if agg is None:
                agg = {
                    "county_fips": fips,
                    "state": state,
                    "month": month,
                    "n_ix_queue_requests": 0,
                    "mw_1_sum": 0.0,
                    "mw_1_n": 0,
                    "n_active": 0,
                    "n_withdrawn": 0,
                    "n_operational": 0,
                    "n_other_status": 0,
                }
                county_month[key] = agg
            agg["n_ix_queue_requests"] += 1
            if mw1 is not None:
                agg["mw_1_sum"] += mw1
                agg["mw_1_n"] += 1
            if status == "active":
                agg["n_active"] += 1
            elif status == "withdrawn":
                agg["n_withdrawn"] += 1
            elif status == "operational":
                agg["n_operational"] += 1
            else:
                agg["n_other_status"] += 1

        if month and state:
            skey = (state, month)
            sagg = state_month.get(skey)
            if sagg is None:
                sagg = {
                    "state": state,
                    "month": month,
                    "n_ix_queue_requests": 0,
                    "n_with_county_fips": 0,
                    "n_state_only": 0,
                    "mw_1_sum": 0.0,
                    "mw_1_n": 0,
                }
                state_month[skey] = sagg
            sagg["n_ix_queue_requests"] += 1
            if fips:
                sagg["n_with_county_fips"] += 1
            else:
                sagg["n_state_only"] += 1
            if mw1 is not None:
                sagg["mw_1_sum"] += mw1
                sagg["mw_1_n"] += 1

    # Write panel CSVs
    panel_fieldnames = [
        "county_fips",
        "state",
        "month",
        "n_ix_queue_requests",
        "mw_1_sum",
        "mw_1_n",
        "n_active",
        "n_withdrawn",
        "n_operational",
        "n_other_status",
        "metric_label",
        "not_data_center_permits",
        "transform_version",
        "denominator_note",
    ]
    denom = (
        "Denominator: all generation/storage interconnection requests in LBNL "
        "Queued Up Complete Queue Data with parseable q_date (or fallback date) "
        "and county FIPS. Not a universe of data-center projects or permits."
    )
    panel_csv.parent.mkdir(parents=True, exist_ok=True)
    panel_rows = []
    with panel_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=panel_fieldnames)
        w.writeheader()
        for key in sorted(county_month.keys()):
            agg = county_month[key]
            row = {
                **agg,
                "mw_1_sum": round(agg["mw_1_sum"], 3),
                "metric_label": METRIC_LABEL,
                "not_data_center_permits": "true",
                "transform_version": TRANSFORM_VERSION,
                "denominator_note": denom,
            }
            w.writerow(row)
            panel_rows.append(row)

    state_fields = [
        "state",
        "month",
        "n_ix_queue_requests",
        "n_with_county_fips",
        "n_state_only",
        "mw_1_sum",
        "mw_1_n",
        "metric_label",
        "not_data_center_permits",
        "transform_version",
        "denominator_note",
    ]
    state_denom = (
        "Denominator: generation/storage interconnection requests with USPS state "
        "and parseable queue month. Includes county-FIPS and state-only rows."
    )
    with panel_state_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=state_fields)
        w.writeheader()
        for key in sorted(state_month.keys()):
            agg = state_month[key]
            w.writerow(
                {
                    **agg,
                    "mw_1_sum": round(agg["mw_1_sum"], 3),
                    "metric_label": METRIC_LABEL,
                    "not_data_center_permits": "true",
                    "transform_version": TRANSFORM_VERSION,
                    "denominator_note": state_denom,
                }
            )

    sample_fields = list(sample_rows[0].keys()) if sample_rows else [
        "q_id",
        "state",
        "county_fips",
        "month",
        "metric_label",
    ]
    with sample_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sample_fields)
        w.writeheader()
        for row in sample_rows:
            w.writerow(row)

    exception_kinds = Counter(e["kind"] for e in qa_exceptions)
    qa: dict[str, Any] = {
        "transform_version": TRANSFORM_VERSION,
        "layer": "G",
        "metric_label": METRIC_LABEL,
        "not_data_center_permits": NOT_DC_PERMITS,
        "content_scope": "generation_storage_interconnection_queues",
        "explicitly_excluded": [
            "data_center_permit_counts",
            "n_projects_proposed",
            "n_projects_approved",
            "n_projects_denied",
            "n_projects_delayed",
        ],
        "raw_path": str(raw_path.relative_to(ROOT)) if raw_path.is_relative_to(ROOT) else str(raw_path),
        "sheet": SHEET_NAME,
        "license_note": "CC BY 4.0 — attribute LBNL / EMP / GridTracker",
        "month_derivation": (
            "Primary: q_date (interconnection request). Fallbacks in order: "
            "ia_date, on_date, wd_date, prop_date."
        ),
        "geo_policy": (
            "county_fips from upstream fips_code via normalize_fips; "
            "else state-only with QA exception; never invent FIPS."
        ),
        "total_queue_rows": n_total,
        "with_county_fips": n_fips,
        "state_only": n_state_only,
        "no_geo": n_no_geo,
        "month_parseable": n_month_ok,
        "month_unparseable": n_month_fail,
        "fips_not_in_gazetteer": n_fips_not_in_gaz,
        "mw_1_present": n_mw_ok,
        "panel_county_month_rows": len(panel_rows),
        "panel_state_month_rows": len(state_month),
        "panel_n_ix_queue_requests_sum": sum(r["n_ix_queue_requests"] for r in panel_rows),
        "coverage_fips_share": round(n_fips / n_total, 4) if n_total else None,
        "coverage_month_share": round(n_month_ok / n_total, 4) if n_total else None,
        "by_status": dict(by_status.most_common()),
        "by_type_clean_top20": dict(by_type.most_common(20)),
        "by_state": dict(sorted(by_state.items())),
        "qa_exception_kinds": dict(exception_kinds),
        "qa_exceptions_capped": qa_exceptions[:200],
        "qa_exceptions_cap_note": "First 200 exceptions embedded; kinds counted fully.",
        "outputs": {
            "panel_county_month_csv": str(panel_csv.relative_to(ROOT)),
            "panel_state_month_csv": str(panel_state_csv.relative_to(ROOT)),
            "sample_csv": str(sample_csv.relative_to(ROOT)),
            "qa_json": str(qa_json.relative_to(ROOT)),
        },
        "generated_at_utc": generated_at.isoformat(),
        "access_date_pt": "2026-09-16",
    }
    qa_json.parent.mkdir(parents=True, exist_ok=True)
    qa_json.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    return qa


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "LBNL Queued Up → county×month / state×month interconnection queue "
            "activity panel (NOT data-center permits)"
        )
    )
    p.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    p.add_argument("--sample-n", type=int, default=SAMPLE_N)
    args = p.parse_args()
    qa = transform(raw_path=args.raw, sample_n=args.sample_n)
    print(f"transform_version={qa['transform_version']}")
    print(f"metric_label={qa['metric_label']}")
    print(f"not_data_center_permits={qa['not_data_center_permits']}")
    print(f"total_queue_rows={qa['total_queue_rows']}")
    print(f"with_county_fips={qa['with_county_fips']}")
    print(f"state_only={qa['state_only']}")
    print(f"month_parseable={qa['month_parseable']}")
    print(f"panel_county_month_rows={qa['panel_county_month_rows']}")
    print(f"panel_state_month_rows={qa['panel_state_month_rows']}")
    print(f"coverage_fips_share={qa['coverage_fips_share']}")
    print(f"outputs={qa['outputs']}")


if __name__ == "__main__":
    main()
