"""Layer C — place/county FIPS crosswalk stubs for Moratorium Nation + AI GridWatch.

Best-effort matching only. Never invent county_fips. Unmatched / ambiguous rows
are logged and left blank. Outputs are stubs for collating before modeling —
not panel event counts.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.geo.fips import load_counties, normalize_fips

ROOT = Path(__file__).resolve().parents[2]

MN_RAW = ROOT / "data" / "raw" / "moratorium_nation" / "moratorium_inventory.csv"
GW_RAW = ROOT / "data" / "raw" / "ai_gridwatch" / "moratoriums.csv"
PLACE_BY_COUNTY = ROOT / "data" / "raw" / "census" / "national_place_by_county2020.txt"

OUT_MN = ROOT / "data" / "processed" / "crosswalks" / "moratorium_nation_place_to_county_v0.csv"
OUT_MN_RES = ROOT / "data" / "processed" / "crosswalks" / "moratorium_nation_place_to_county_v0_residuals.csv"
OUT_GW = ROOT / "data" / "processed" / "crosswalks" / "ai_gridwatch_place_to_county_v0.csv"
OUT_GW_RES = ROOT / "data" / "processed" / "crosswalks" / "ai_gridwatch_place_to_county_v0_residuals.csv"
OUT_QA = ROOT / "data" / "processed" / "qa" / "c_moratoria_geo_stub_v0_qa.json"

TRANSFORM_VERSION = "c_moratoria_geo_stub_v0"

_LEGAL_SUFFIXES = (
    " county",
    " parish",
    " borough",
    " census area",
    " municipality",
    " city and borough",
    " charter township",
    " township",
    " town",
    " village",
    " city",
    " cdp",
    " borough",
)


def _norm_place(value: str) -> str:
    s = (value or "").strip().lower()
    s = s.replace(".", "")
    s = re.sub(r"['’]", "", s)
    s = re.sub(r"\s+", " ", s)
    s = s.replace("saint ", "st ")
    # Drop parenthetical county hints: "Tonawanda (Erie Co.)"
    s = re.sub(r"\s*\([^)]*\)\s*", " ", s).strip()
    s = re.sub(r"\s+", " ", s)
    changed = True
    while changed:
        changed = False
        for suf in _LEGAL_SUFFIXES:
            if s.endswith(suf):
                s = s[: -len(suf)].strip()
                changed = True
                break
    return s.strip()


def _norm_state(value: str) -> Optional[str]:
    s = (value or "").strip().upper()
    if len(s) == 2 and s.isalpha():
        return s
    return None


def _month_from_iso(value: str) -> Optional[str]:
    s = (value or "").strip()
    if not s:
        return None
    # YYYY-MM-DD or YYYY-MM or YYYY
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:7]
    if re.match(r"^\d{4}-\d{2}$", s):
        return s
    if re.match(r"^\d{4}$", s):
        return None  # year-only: do not invent month
    return None


class GeoIndex:
    def __init__(self) -> None:
        self.by_county: dict[tuple[str, str], list[str]] = defaultdict(list)
        self.by_place: dict[tuple[str, str], list[str]] = defaultdict(list)
        self._load()

    def _load(self) -> None:
        for c in load_counties():
            self.by_county[(c.state, _norm_place(c.name))].append(c.fips)
        if not PLACE_BY_COUNTY.exists():
            return
        with PLACE_BY_COUNTY.open(encoding="latin-1", errors="replace", newline="") as f:
            reader = csv.DictReader(f, delimiter="|")
            for row in reader:
                st = _norm_state(row.get("STATE") or "")
                pname = (row.get("PLACENAME") or "").strip()
                sfp = (row.get("STATEFP") or "").strip()
                cfp = (row.get("COUNTYFP") or "").strip()
                if not st or not pname or not sfp or not cfp:
                    continue
                fips = normalize_fips(sfp.zfill(2) + cfp.zfill(3))
                if not fips:
                    continue
                self.by_place[(st, _norm_place(pname))].append(fips)

        # dedupe lists while preserving order
        for d in (self.by_county, self.by_place):
            for k, vals in list(d.items()):
                seen: list[str] = []
                for v in vals:
                    if v not in seen:
                        seen.append(v)
                d[k] = seen

    def match(
        self,
        state: str,
        name: str,
        *,
        jurisdiction_type: str = "",
    ) -> tuple[str, Optional[str], list[str]]:
        """Return (match_kind, county_fips|None, candidates)."""
        st = _norm_state(state)
        raw = (name or "").strip()
        if not st or not raw:
            return "no_geo_input", None, []
        low = raw.lower()
        if "statewide" in low or "(statewide)" in low:
            return "state_only", None, []

        n = _norm_place(raw)
        jt = (jurisdiction_type or "").strip().lower()
        looks_county = (
            "county" in jt
            or "parish" in jt
            or bool(re.search(r"\bcounty\b", raw, re.I))
            or bool(re.search(r"\bparish\b", raw, re.I))
        )

        county_hits = self.by_county.get((st, n), [])
        if looks_county:
            if len(county_hits) == 1:
                return "county", county_hits[0], []
            if len(county_hits) > 1:
                return "ambiguous_county", None, county_hits

        place_hits = self.by_place.get((st, n), [])
        if len(place_hits) == 1:
            return "place", place_hits[0], []
        if len(place_hits) > 1:
            return "ambiguous_place", None, place_hits

        # County name without explicit type (e.g. "Prince William County" already stripped)
        if len(county_hits) == 1:
            return "county_name", county_hits[0], []
        if len(county_hits) > 1:
            return "ambiguous_county", None, county_hits

        return "unmatched", None, []


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def transform_moratorium_nation(idx: GeoIndex) -> dict[str, Any]:
    if not MN_RAW.exists():
        raise FileNotFoundError(f"Missing {MN_RAW}; run: make fetch-moratorium-nation")
    with MN_RAW.open(newline="", encoding="utf-8", errors="replace") as f:
        raw_rows = list(csv.DictReader(f))

    out_rows: list[dict[str, Any]] = []
    residuals: list[dict[str, Any]] = []
    kinds: Counter[str] = Counter()
    matched = 0
    month_ok = 0

    for row in raw_rows:
        kind, fips, cands = idx.match(
            row.get("state_abbrev") or "",
            row.get("jurisdiction") or "",
            jurisdiction_type=row.get("jurisdiction_type") or "",
        )
        kinds[kind] += 1
        month = _month_from_iso(row.get("date_enacted_iso") or "")
        if month:
            month_ok += 1
        if fips:
            matched += 1
        rec = {
            "source": "moratorium_nation",
            "moratorium_id": row.get("moratorium_id") or "",
            "state": (row.get("state_abbrev") or "").strip().upper(),
            "jurisdiction": row.get("jurisdiction") or "",
            "jurisdiction_type": row.get("jurisdiction_type") or "",
            "enacted_status": row.get("enacted_status") or "",
            "date_enacted_iso": row.get("date_enacted_iso") or "",
            "month": month or "",
            "sectors": row.get("sectors") or "",
            "county_fips": fips or "",
            "match_kind": kind,
            "candidate_fips": "|".join(cands) if cands else "",
            "transform_version": TRANSFORM_VERSION,
            "geo_policy": "best_effort_place_county_stub_no_invented_fips",
        }
        out_rows.append(rec)
        if not fips:
            residuals.append(rec)

    fields = list(out_rows[0].keys()) if out_rows else [
        "source",
        "state",
        "jurisdiction",
        "county_fips",
        "match_kind",
    ]
    _write_csv(OUT_MN, out_rows, fields)
    _write_csv(OUT_MN_RES, residuals, fields)
    return {
        "source": "moratorium_nation",
        "raw_path": str(MN_RAW.relative_to(ROOT)),
        "total_rows": len(raw_rows),
        "matched_county_fips": matched,
        "match_rate": round(matched / len(raw_rows), 4) if raw_rows else None,
        "month_parseable": month_ok,
        "by_match_kind": dict(kinds),
        "outputs": {
            "crosswalk_csv": str(OUT_MN.relative_to(ROOT)),
            "residuals_csv": str(OUT_MN_RES.relative_to(ROOT)),
        },
    }


def transform_ai_gridwatch(idx: GeoIndex) -> dict[str, Any]:
    if not GW_RAW.exists():
        raise FileNotFoundError(f"Missing {GW_RAW}; run: make fetch-ai-gridwatch")
    with GW_RAW.open(newline="", encoding="utf-8", errors="replace") as f:
        raw_rows = list(csv.DictReader(f))

    out_rows: list[dict[str, Any]] = []
    residuals: list[dict[str, Any]] = []
    kinds: Counter[str] = Counter()
    matched = 0
    month_ok = 0

    for row in raw_rows:
        kind, fips, cands = idx.match(
            row.get("state") or "",
            row.get("locality") or "",
            jurisdiction_type="",
        )
        kinds[kind] += 1
        month = _month_from_iso(row.get("date") or "")
        if month:
            month_ok += 1
        if fips:
            matched += 1
        rec = {
            "source": "ai_gridwatch",
            "id": row.get("id") or "",
            "state": (row.get("state") or "").strip().upper(),
            "locality": row.get("locality") or "",
            "level": row.get("level") or "",
            "status": row.get("status") or "",
            "effective_status": row.get("effective_status") or "",
            "date": row.get("date") or "",
            "date_precision": row.get("date_precision") or "",
            "month": month or "",
            "county_fips": fips or "",
            "match_kind": kind,
            "candidate_fips": "|".join(cands) if cands else "",
            "transform_version": TRANSFORM_VERSION,
            "geo_policy": "best_effort_place_county_stub_no_invented_fips",
        }
        out_rows.append(rec)
        if not fips:
            residuals.append(rec)

    fields = list(out_rows[0].keys()) if out_rows else [
        "source",
        "state",
        "locality",
        "county_fips",
        "match_kind",
    ]
    _write_csv(OUT_GW, out_rows, fields)
    _write_csv(OUT_GW_RES, residuals, fields)
    return {
        "source": "ai_gridwatch",
        "raw_path": str(GW_RAW.relative_to(ROOT)),
        "total_rows": len(raw_rows),
        "matched_county_fips": matched,
        "match_rate": round(matched / len(raw_rows), 4) if raw_rows else None,
        "month_parseable": month_ok,
        "by_match_kind": dict(kinds),
        "outputs": {
            "crosswalk_csv": str(OUT_GW.relative_to(ROOT)),
            "residuals_csv": str(OUT_GW_RES.relative_to(ROOT)),
        },
    }


def transform() -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc)
    idx = GeoIndex()
    mn = transform_moratorium_nation(idx)
    gw = transform_ai_gridwatch(idx)
    qa = {
        "transform_version": TRANSFORM_VERSION,
        "layer": "C",
        "policy": (
            "Place/county FIPS crosswalk stubs only. Blank county_fips when unmatched "
            "or ambiguous — never invent. Not panel event counts; collate before modeling."
        ),
        "not_invented": [
            "county_fips_for_unmatched",
            "ordinance_event_counts",
            "data_center_permit_outcomes",
        ],
        "geo_inputs": {
            "counties_gazetteer": "data/raw/census/2024_Gaz_counties_national.txt",
            "place_by_county": str(PLACE_BY_COUNTY.relative_to(ROOT))
            if PLACE_BY_COUNTY.exists()
            else None,
            "place_by_county_present": PLACE_BY_COUNTY.exists(),
            "county_keys": len(idx.by_county),
            "place_keys": len(idx.by_place),
        },
        "moratorium_nation": mn,
        "ai_gridwatch": gw,
        "outputs": {
            "qa_json": str(OUT_QA.relative_to(ROOT)),
            **{f"mn_{k}": v for k, v in mn["outputs"].items()},
            **{f"gw_{k}": v for k, v in gw["outputs"].items()},
        },
        "generated_at_utc": generated_at.isoformat(),
        "access_date_pt": "2026-09-16",
    }
    OUT_QA.parent.mkdir(parents=True, exist_ok=True)
    OUT_QA.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    return qa


def main() -> None:
    argparse.ArgumentParser(
        description="C-layer moratoria place→county FIPS crosswalk stubs (no invented FIPS)"
    ).parse_args()
    qa = transform()
    print(f"transform_version={qa['transform_version']}")
    print(f"moratorium_nation={qa['moratorium_nation']}")
    print(f"ai_gridwatch={qa['ai_gridwatch']}")
    print(f"outputs={qa['outputs']}")


if __name__ == "__main__":
    main()
