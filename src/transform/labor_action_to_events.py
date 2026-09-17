"""Labor Action Tracker Pages JSON → thin events sample (layer E complement).

Filter: lat_rules_v0 (docs/filters/lat_ai_keywords_v0.md).
Precision over recall. Stdlib only. No invented matches or FIPS.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.schema.types import (
    Event,
    Grievance,
    Layer,
    Referent,
    Stance,
    TAXONOMY_VERSION,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW = ROOT / "data" / "raw" / "labor_action" / "labor_actions.json"
RAW_RELATIVE = "data/raw/labor_action/labor_actions.json"

OUT_EVENTS_JSONL = ROOT / "data" / "processed" / "events" / "lat_ai_related_v0.jsonl"
OUT_EVENTS_CSV = ROOT / "data" / "processed" / "events" / "lat_ai_related_v0.csv"
OUT_PANEL_CSV = ROOT / "data" / "processed" / "panel" / "lat_mobilization_counts_v0.csv"
OUT_QA_JSON = ROOT / "data" / "processed" / "qa" / "lat_ai_related_v0_qa.json"

FILTER_VERSION = "lat_rules_v0"
CLASSIFIER_VERSION = f"{TAXONOMY_VERSION}+{FILTER_VERSION}"

STATE_NAME_TO_USPS: dict[str, str] = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME",
    "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE",
    "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY", "Puerto Rico": "PR",
}

ALLOWLIST: list[tuple[str, str]] = [
    ("data_center", r"data[\s\-]?cent(?:er|re)s?"),
    ("datacenter", r"datacent(?:er|re)s?"),
    ("server_farm", r"server\s+farms?"),
    ("hyperscale", r"hyperscale"),
    ("artificial_intelligence", r"artificial\s+intelligence"),
    ("agi", r"artificial\s+general\s+intelligence|\bAGIs?\b"),
    ("asi", r"artificial\s+superintelligence|\bASIs?\b"),
    ("generative_ai", r"generative\s+AI"),
    ("chatgpt", r"chatgpt"),
    ("openai", r"openai"),
    ("machine_learning", r"\bmachine\s+learning\b"),
    ("llm", r"\bLLMs?\b"),
    ("gpu", r"\bGPUs?\b"),
    ("automation", r"\bautomation\b"),
    ("robotic", r"\brobotic"),
    ("robot", r"\brobots?\b"),
    ("ai_word", r"\bAI\b"),
]

CRYPTO_PATTERNS = [r"crypto(?:currency)?\s+mining", r"bitcoin\s+mining"]
CRYPTO_CONTEXT = [
    r"data[\s\-]?cent(?:er|re)", r"datacent(?:er|re)", r"hyperscale", r"server\s+farm",
    r"\bAI\b", r"artificial\s+intelligence", r"electricit", r"\benergy\b", r"\bpower\b", r"\bgrid\b",
]
ROBOT_ONLY = {"robot", "robotic"}

GRIEVANCE_KEYWORDS: list[tuple[Grievance, tuple[str, ...]]] = [
    (Grievance.ENERGY_GRID_COST, (r"electricit", r"\benergy\b", r"\bgrid\b", r"power\s+rate", r"\bpower\b")),
    (Grievance.WATER, (r"\bwater\b", r"aquifer", r"wastewater", r"drought")),
    (Grievance.LAND_USE_NOISE_AESTHETICS, (r"rezon", r"\bzoning\b", r"\bnoise\b", r"farmland", r"land\s+use", r"\bsiting\b")),
    (Grievance.TAX_ABATEMENT_FISCAL, (r"tax\s+break", r"tax\s+abatement", r"\bPILOT\b", r"fiscal", r"subsid", r"incentive")),
    (Grievance.JOBS_DISPLACEMENT, (r"\bjob\b", r"\bjobs\b", r"displac", r"lay\s*off", r"layoff", r"automat", r"\bwage", r"\bpay\b", r"bargain", r"contract", r"staffing", r"surveillance")),
    (Grievance.SAFETY_CONTROL, (r"health and safety", r"\bsafety\b", r"surveillance", r"monitor")),
    (Grievance.DATA_PRIVACY, (r"\bprivacy\b", r"surveillance", r"monitor")),
]

_ALLOW_RE = [(n, re.compile(p, re.I)) for n, p in ALLOWLIST]
_CRYPTO_RE = [re.compile(p, re.I) for p in CRYPTO_PATTERNS]
_CRYPTO_CTX_RE = [re.compile(p, re.I) for p in CRYPTO_CONTEXT]
_GRIEVANCE_RE = [(g, [re.compile(p, re.I) for p in pats]) for g, pats in GRIEVANCE_KEYWORDS]


def _join_list(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        return " ".join(str(x) for x in val if x is not None)
    return str(val)


def action_text_blob(rec: dict[str, Any]) -> str:
    return " ".join(
        [
            str(rec.get("Employer") or ""),
            str(rec.get("Labor_Organization") or ""),
            str(rec.get("Local") or ""),
            str(rec.get("Notes") or ""),
            _join_list(rec.get("Industry")),
            _join_list(rec.get("Worker_demands")),
        ]
    )


def match_rules(blob: str) -> list[str]:
    hits = [name for name, cre in _ALLOW_RE if cre.search(blob)]
    if any(cre.search(blob) for cre in _CRYPTO_RE) and any(
        cre.search(blob) for cre in _CRYPTO_CTX_RE
    ):
        hits.append("crypto_mining_with_context")
    if hits and set(hits) <= ROBOT_ONLY:
        return []
    return hits


def map_grievances(blob: str) -> list[Grievance]:
    return [g for g, patterns in _GRIEVANCE_RE if any(p.search(blob) for p in patterns)]


def parse_date(val: Any) -> Optional[date]:
    if val is None or val == "":
        return None
    try:
        return date.fromisoformat(str(val).strip()[:10])
    except ValueError:
        return None


def state_from_location(loc: dict[str, Any]) -> Optional[str]:
    raw = str(loc.get("State") or "").strip()
    if not raw:
        return None
    if len(raw) == 2 and raw.isalpha():
        return raw.upper()
    return STATE_NAME_TO_USPS.get(raw)


def event_id_for(sid: str) -> str:
    return f"E:lat:{hashlib.sha256(sid.encode('utf-8')).hexdigest()[:20]}"


def load_actions(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected object keyed by action id, got {type(data)}")
    return {str(k): v for k, v in data.items() if isinstance(v, dict)}


def transform(path: Path | None = None) -> dict[str, Any]:
    path = path or DEFAULT_RAW
    if not path.exists():
        raise SystemExit(f"missing raw JSON: {path}; run: make fetch-labor-action")

    actions = load_actions(path)
    ingested_at = datetime.now(timezone.utc)
    events: list[Event] = []
    qa_flags: list[dict[str, Any]] = []
    rule_hit_counter: Counter[str] = Counter()
    n_matched_actions = 0
    n_skipped_bad_state = 0
    n_skipped_bad_date = 0
    n_location_rows = 0
    missing_fips = 0

    for action_id, rec in actions.items():
        blob = action_text_blob(rec)
        hits = match_rules(blob)
        if not hits:
            continue
        n_matched_actions += 1
        for h in hits:
            rule_hit_counter[h] += 1

        ed = parse_date(rec.get("Start_date"))
        if ed is None:
            n_skipped_bad_date += 1
            qa_flags.append({"action_id": action_id, "skip_reason": "bad_date", "rule_hits": hits})
            continue

        locs = rec.get("locations") if isinstance(rec.get("locations"), list) else []
        if not locs:
            locs = [{}]

        grievances = map_grievances(blob)
        demands = _join_list(rec.get("Worker_demands"))
        employer = str(rec.get("Employer") or "").strip()
        action_type = str(rec.get("Action_type") or "").strip()
        title = f"{action_type}: {employer}".strip(": ").strip() or None
        sources = rec.get("sources") if isinstance(rec.get("sources"), list) else []
        source_url = sources[0] if sources else None

        for loc in locs:
            if not isinstance(loc, dict):
                loc = {}
            state = state_from_location(loc)
            if state is None:
                n_skipped_bad_state += 1
                qa_flags.append(
                    {
                        "action_id": action_id,
                        "skip_reason": "bad_state",
                        "loc_state": loc.get("State"),
                        "rule_hits": hits,
                    }
                )
                continue

            n_location_rows += 1
            missing_fips += 1  # LAT has no county FIPS — leave blank
            loc_id = loc.get("id")
            sid = f"lat:{action_id}:loc:{loc_id if loc_id is not None else 'na'}"
            try:
                ev = Event(
                    event_id=event_id_for(sid),
                    state=state,
                    event_date=ed,
                    event_month=ed.strftime("%Y-%m"),
                    layer=Layer.E,
                    source="labor_action_tracker",
                    county_fips=None,
                    source_url=str(source_url) if source_url else None,
                    source_record_id=sid,
                    grievance=grievances,
                    stance=Stance.OPPOSE,
                    referent=Referent.AMBIGUOUS,
                    confidence=None,
                    classifier_version=CLASSIFIER_VERSION,
                    title=title,
                    summary=demands or None,
                    raw_payload_path=RAW_RELATIVE,
                    ingested_at=ingested_at,
                )
            except ValueError as exc:
                qa_flags.append(
                    {
                        "action_id": action_id,
                        "skip_reason": f"event_validation:{exc}",
                        "rule_hits": hits,
                    }
                )
                continue
            events.append(ev)
            qa_flags.append(
                {
                    "action_id": action_id,
                    "source_record_id": sid,
                    "rule_hits": hits,
                    "city": loc.get("City"),
                    "state": state,
                    "county_fips": None,
                    "missing_fips": True,
                }
            )

    OUT_EVENTS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_EVENTS_JSONL.open("w", encoding="utf-8") as f:
        for ev in events:
            d = asdict(ev)
            d["event_date"] = ev.event_date.isoformat()
            d["layer"] = ev.layer.value
            d["stance"] = ev.stance.value if ev.stance else None
            d["referent"] = ev.referent.value if ev.referent else None
            d["grievance"] = [g.value for g in ev.grievance]
            if ev.ingested_at is not None:
                d["ingested_at"] = ev.ingested_at.isoformat()
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    fieldnames = [
        "event_id", "county_fips", "state", "event_date", "event_month", "layer",
        "source", "source_url", "source_record_id", "grievance", "stance", "referent",
        "confidence", "classifier_version", "title", "summary", "raw_payload_path",
        "ingested_at",
    ]
    with OUT_EVENTS_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for ev in events:
            w.writerow(
                {
                    "event_id": ev.event_id,
                    "county_fips": ev.county_fips or "",
                    "state": ev.state,
                    "event_date": ev.event_date.isoformat(),
                    "event_month": ev.event_month,
                    "layer": ev.layer.value,
                    "source": ev.source,
                    "source_url": ev.source_url or "",
                    "source_record_id": ev.source_record_id or "",
                    "grievance": json.dumps([g.value for g in ev.grievance]),
                    "stance": ev.stance.value if ev.stance else "",
                    "referent": ev.referent.value if ev.referent else "",
                    "confidence": "" if ev.confidence is None else ev.confidence,
                    "classifier_version": ev.classifier_version or "",
                    "title": ev.title or "",
                    "summary": ev.summary or "",
                    "raw_payload_path": ev.raw_payload_path or "",
                    "ingested_at": ev.ingested_at.isoformat() if ev.ingested_at else "",
                }
            )

    OUT_PANEL_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PANEL_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "county_fips", "state", "month", "n_mobilization",
                "taxonomy_version", "filter_version",
            ],
        )
        w.writeheader()

    zero_matches = n_matched_actions == 0
    qa = {
        "filter_version": FILTER_VERSION,
        "classifier_version": CLASSIFIER_VERSION,
        "raw_path": RAW_RELATIVE,
        "total_actions": len(actions),
        "matched_actions": n_matched_actions,
        "match_rate_actions": round(n_matched_actions / len(actions), 6) if actions else 0.0,
        "event_rows_written": len(events),
        "location_rows_from_matches": n_location_rows,
        "skipped_bad_date": n_skipped_bad_date,
        "skipped_bad_state": n_skipped_bad_state,
        "missing_fips_among_events": missing_fips,
        "missing_fips_note": (
            "LAT locations expose City/State/Zip/lat/lon only — county_fips left blank; "
            "no invented FIPS. Panel CSV header-only until a zip/place→county crosswalk ships."
        ),
        "rule_hit_counts": dict(rule_hit_counter),
        "zero_keyword_matches": zero_matches,
        "zero_matches_note": (
            "Filter yielded zero AI/tech/data-center keyword matches in scanned text fields."
            if zero_matches
            else None
        ),
        "coverage_caveat": (
            "LAT is manual; strikes relatively comprehensive from ~2021; "
            "labor protests are not a complete count. Complement to CCC, not a replacement."
        ),
        "outputs": {
            "events_csv": str(OUT_EVENTS_CSV.relative_to(ROOT)),
            "events_jsonl": str(OUT_EVENTS_JSONL.relative_to(ROOT)),
            "panel_csv": str(OUT_PANEL_CSV.relative_to(ROOT)),
        },
        "sample_flags": qa_flags[:30],
        "recorded_at_utc": ingested_at.isoformat(),
    }
    OUT_QA_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_QA_JSON.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {k: qa[k] for k in (
                "total_actions", "matched_actions", "match_rate_actions",
                "event_rows_written", "missing_fips_among_events",
                "zero_keyword_matches", "rule_hit_counts",
            )},
            indent=2,
        )
    )
    return qa


def main() -> None:
    p = argparse.ArgumentParser(description="LAT JSON → AI-related events stub")
    p.add_argument("--raw", type=Path, default=None)
    args = p.parse_args()
    transform(args.raw)


if __name__ == "__main__":
    main()
