"""CCC phase-3 CSV → events (layer E) + thin mobilization panel slice.

Filter version: ccc_rules_v0 (see docs/filters/ccc_ai_keywords_v0.md).
Precision over recall. Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from src.geo.fips import normalize_fips
from src.schema.types import (
    Event,
    Grievance,
    Layer,
    Referent,
    Stance,
    TAXONOMY_VERSION,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW = ROOT / "data" / "raw" / "ccc" / "ccc-phase3-public.csv"
RAW_RELATIVE = "data/raw/ccc/ccc-phase3-public.csv"

OUT_EVENTS_JSONL = ROOT / "data" / "processed" / "events" / "ccc_ai_related_v0.jsonl"
OUT_EVENTS_CSV = ROOT / "data" / "processed" / "events" / "ccc_ai_related_v0.csv"
OUT_PANEL_CSV = ROOT / "data" / "processed" / "panel" / "ccc_mobilization_counts_v0.csv"
OUT_QA_JSON = ROOT / "data" / "processed" / "qa" / "ccc_ai_related_v0_qa.json"

FILTER_VERSION = "ccc_rules_v0"
CLASSIFIER_VERSION = f"{TAXONOMY_VERSION}+{FILTER_VERSION}"

# Fields searched for allowlist / grievance / referent heuristics.
TEXT_FIELDS = (
    "title",
    "claims_summary",
    "claims_verbatim",
    "issue_tags_summary",
    "issue_tags_verbatim",
    "issues",
    "organizations",
    "targets",
    "notes",
)

SOURCE_FIELDS = tuple(f"source{i}" for i in range(1, 31))

# ---------------------------------------------------------------------------
# RULES — versioned keyword allowlist (keep in sync with docs/filters/)
# ---------------------------------------------------------------------------

RULES: dict[str, Any] = {
    "version": FILTER_VERSION,
    "precision_over_recall": True,
    # Each entry: (name, compiled later from pattern string)
    "allowlist": [
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
        # Whole-word AI last among AI phrases for documentation clarity;
        # matching is independent per pattern.
        ("ai_word", r"\bAI\b"),
    ],
    # Crypto / mining only with energy or AI/data-center co-occurrence.
    "crypto_patterns": [
        r"crypto(?:currency)?\s+mining",
        r"bitcoin\s+mining",
    ],
    "crypto_context": [
        r"data[\s\-]?cent(?:er|re)",
        r"datacent(?:er|re)",
        r"hyperscale",
        r"server\s+farm",
        r"\bAI\b",
        r"artificial\s+intelligence",
        r"electricit",
        r"\benergy\b",
        r"\bpower\b",
        r"\bgrid\b",
    ],
    # If the only hits are robot-family, drop (slogan FP guard).
    "robot_only_names": {"robot", "robotic"},
}

# Grievance keyword → taxonomy id (ordered; primary = first matched category).
GRIEVANCE_KEYWORDS: list[tuple[Grievance, tuple[str, ...]]] = [
    (
        Grievance.ENERGY_GRID_COST,
        (
            r"electricit",
            r"\benergy\b",
            r"\bgrid\b",
            r"power\s+rate",
            r"utility\s+rate",
            r"rate\s+hike",
            r"power\s+plant",
        ),
    ),
    (
        Grievance.WATER,
        (r"\bwater\b", r"aquifer", r"wastewater", r"drought"),
    ),
    (
        Grievance.LAND_USE_NOISE_AESTHETICS,
        (
            r"rezon",
            r"\bzoning\b",
            r"\bnoise\b",
            r"farmland",
            r"land\s+use",
            r"aesthetics",
            r"\bsiting\b",
        ),
    ),
    (
        Grievance.TAX_ABATEMENT_FISCAL,
        (
            r"tax\s+break",
            r"tax\s+abatement",
            r"\bPILOT\b",
            r"fiscal",
            r"subsid",
            r"incentive",
        ),
    ),
    (
        Grievance.JOBS_DISPLACEMENT,
        (
            r"\bjobs?\b",
            r"displacement",
            r"\bautomation\b",
            r"replace(?:d|ment)?\s+by\s+AI",
            r"\bunion",
            r"workers?\s+rights",
            r"liv(?:e|ing)\s+wage",
        ),
    ),
    (
        Grievance.SCHOOLS_EDUCATION,
        (
            r"\bschool",
            r"\beducation\b",
            r"curriculum",
            r"students?\b",
            r"university",
            r"\bCSU\b",
        ),
    ),
    (
        Grievance.SAFETY_CONTROL,
        (
            r"\bsafety\b",
            r"military",
            r"weapon",
            r"WMD",
            r"surveillance\s+camera",
            r"catastrophic",
            r"superintelligence",
            r"\bAGI\b",
        ),
    ),
    (
        Grievance.DATA_PRIVACY,
        (
            r"\bprivacy\b",
            r"surveillance",
            r"personal\s+data",
            r"\bbiometric",
        ),
    ),
    (
        Grievance.CREATIVE_WORK_IP,
        (
            r"copyright",
            r"stolen\s+work",
            r"training\s+on",
            r"creator",
            r"intellectual\s+property",
            r"\bIP\b",
        ),
    ),
]

LOCAL_REFERENT_PATTERNS = [
    r"data[\s\-]?cent(?:er|re)",
    r"datacent(?:er|re)",
    r"rezon",
    r"\bzoning\b",
    r"proposed\s+",
    r"\bcounty\b",
    r"\bcity\s+council\b",
    r"project\s+\w+",
    r"server\s+farm",
    r"hyperscale",
    r"local\s+",
]

NATIONAL_REFERENT_PATTERNS = [
    r"\bfederal\b",
    r"\bcongress\b",
    r"\bnational\b",
    r"openai",
    r"chatgpt",
    r"artificial\s+general\s+intelligence",
    r"\bAGI\b",
    r"artificial\s+superintelligence",
    r"generative\s+AI",
    r"white\s+house",
]

# USPS already expected on CCC `state`; map common full names / territories if needed.
STATE_NAME_TO_USPS = {
    "ALABAMA": "AL",
    "ALASKA": "AK",
    "ARIZONA": "AZ",
    "ARKANSAS": "AR",
    "CALIFORNIA": "CA",
    "COLORADO": "CO",
    "CONNECTICUT": "CT",
    "DELAWARE": "DE",
    "DISTRICT OF COLUMBIA": "DC",
    "FLORIDA": "FL",
    "GEORGIA": "GA",
    "HAWAII": "HI",
    "IDAHO": "ID",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "IOWA": "IA",
    "KANSAS": "KS",
    "KENTUCKY": "KY",
    "LOUISIANA": "LA",
    "MAINE": "ME",
    "MARYLAND": "MD",
    "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI",
    "MINNESOTA": "MN",
    "MISSISSIPPI": "MS",
    "MISSOURI": "MO",
    "MONTANA": "MT",
    "NEBRASKA": "NE",
    "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM",
    "NEW YORK": "NY",
    "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND",
    "OHIO": "OH",
    "OKLAHOMA": "OK",
    "OREGON": "OR",
    "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN",
    "TEXAS": "TX",
    "UTAH": "UT",
    "VERMONT": "VT",
    "VIRGINIA": "VA",
    "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI",
    "WYOMING": "WY",
    "PUERTO RICO": "PR",
    "GUAM": "GU",
    "AMERICAN SAMOA": "AS",
    "NORTHERN MARIANA ISLANDS": "MP",
    "VIRGIN ISLANDS": "VI",
}


def _compile_rules() -> tuple[list[tuple[str, re.Pattern[str]]], list[re.Pattern[str]], list[re.Pattern[str]]]:
    allow = [(name, re.compile(pat, re.I)) for name, pat in RULES["allowlist"]]
    crypto = [re.compile(p, re.I) for p in RULES["crypto_patterns"]]
    crypto_ctx = [re.compile(p, re.I) for p in RULES["crypto_context"]]
    return allow, crypto, crypto_ctx


_ALLOW, _CRYPTO, _CRYPTO_CTX = _compile_rules()
_GRIEVANCE_COMPILED = [
    (g, [re.compile(p, re.I) for p in pats]) for g, pats in GRIEVANCE_KEYWORDS
]
_LOCAL_RE = [re.compile(p, re.I) for p in LOCAL_REFERENT_PATTERNS]
_NATIONAL_RE = [re.compile(p, re.I) for p in NATIONAL_REFERENT_PATTERNS]


def _clean_cell(value: Optional[str]) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if not s or s.upper() in {"NA", "N/A", "NONE", "NULL", "."}:
        return ""
    return s


def row_text_blob(row: dict[str, str]) -> str:
    parts = [_clean_cell(row.get(f)) for f in TEXT_FIELDS]
    return " ".join(p for p in parts if p)


def match_allowlist(blob: str) -> list[str]:
    """Return sorted unique rule names that hit; empty → not AI-related under v0."""
    if not blob:
        return []
    hits: list[str] = []
    for name, cre in _ALLOW:
        if cre.search(blob):
            hits.append(name)

    crypto_hit = any(cre.search(blob) for cre in _CRYPTO)
    if crypto_hit and any(cre.search(blob) for cre in _CRYPTO_CTX):
        hits.append("crypto_mining_contextual")

    # Robot-only guard: slogan titles without other AI/data-center signal.
    robot_only = RULES["robot_only_names"]
    hit_set = set(hits)
    if hit_set and hit_set <= robot_only:
        return []

    # Stable order as declared in RULES allowlist, then crypto tag.
    order = [n for n, _ in RULES["allowlist"]] + ["crypto_mining_contextual"]
    return [n for n in order if n in hit_set]


def normalize_state(raw: Optional[str], fallback: Optional[str] = None) -> Optional[str]:
    for candidate in (raw, fallback):
        s = _clean_cell(candidate)
        if not s:
            continue
        if len(s) == 2 and s.isalpha():
            return s.upper()
        mapped = STATE_NAME_TO_USPS.get(s.upper())
        if mapped:
            return mapped
    return None


def parse_event_date(raw: Optional[str]) -> Optional[date]:
    s = _clean_cell(raw)
    if not s:
        return None
    # Expect YYYY-MM-DD; tolerate other ISO prefixes.
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def first_source_url(row: dict[str, str]) -> Optional[str]:
    for f in SOURCE_FIELDS:
        v = _clean_cell(row.get(f))
        if v.startswith("http://") or v.startswith("https://"):
            return v
    for f in SOURCE_FIELDS:
        v = _clean_cell(row.get(f))
        if v:
            return v
    return None


def parse_confidence(raw: Optional[str]) -> Optional[float]:
    s = _clean_cell(raw)
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def map_grievances(blob: str) -> list[Grievance]:
    out: list[Grievance] = []
    for g, patterns in _GRIEVANCE_COMPILED:
        if any(p.search(blob) for p in patterns):
            out.append(g)
    return out


def infer_referent(blob: str) -> Referent:
    local = any(p.search(blob) for p in _LOCAL_RE)
    national = any(p.search(blob) for p in _NATIONAL_RE)
    if local and not national:
        return Referent.LOCAL
    if national and not local:
        return Referent.NATIONAL
    if local and national:
        # Local siting language wins when both present (e.g. "AI data center in Botetourt").
        if re.search(r"data[\s\-]?cent(?:er|re)|datacent(?:er|re)|rezon|zoning|server\s+farm", blob, re.I):
            return Referent.LOCAL
        return Referent.AMBIGUOUS
    return Referent.AMBIGUOUS


def source_record_id(row: dict[str, str], event_date: date, state: str) -> str:
    """Stable upstream-ish key from date + locality + state + title (+ claims snippet)."""
    locality = _clean_cell(row.get("resolved_locality")) or _clean_cell(row.get("locality"))
    title = _clean_cell(row.get("title"))
    claims = _clean_cell(row.get("claims_summary"))
    basis = "|".join(
        [
            event_date.isoformat(),
            locality.lower(),
            state,
            title.lower(),
            claims.lower()[:200],
        ]
    )
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    return f"ccc:{event_date.isoformat()}:{state}:{digest}"


def event_id_from_record(source_record_id: str) -> str:
    digest = hashlib.sha256(source_record_id.encode("utf-8")).hexdigest()[:20]
    return f"E:ccc:{digest}"


def row_to_event(
    row: dict[str, str],
    *,
    rule_hits: list[str],
    ingested_at: datetime,
) -> tuple[Optional[Event], dict[str, Any]]:
    """Map one matching CCC row → Event. Returns (event_or_None, qa_flags)."""
    flags: dict[str, Any] = {"rule_hits": rule_hits}
    ed = parse_event_date(row.get("date"))
    if ed is None:
        flags["skip_reason"] = "bad_date"
        return None, flags

    state = normalize_state(row.get("state"), row.get("resolved_state"))
    if state is None:
        flags["skip_reason"] = "bad_state"
        return None, flags

    fips = normalize_fips(row.get("fips_code"))
    if fips is None:
        flags["missing_fips"] = True

    blob = row_text_blob(row)
    grievances = map_grievances(blob)
    referent = infer_referent(blob)
    # Stance: default oppose for protest mobilization (documented assumption).
    stance = Stance.OPPOSE
    flags["stance_assumption"] = "default_oppose_protest"
    flags["ccc_valence"] = _clean_cell(row.get("valence")) or None

    sid = source_record_id(row, ed, state)
    eid = event_id_from_record(sid)
    title = _clean_cell(row.get("title")) or None
    summary = _clean_cell(row.get("claims_summary")) or None
    conf = parse_confidence(row.get("conf"))

    try:
        ev = Event(
            event_id=eid,
            state=state,
            event_date=ed,
            event_month=ed.strftime("%Y-%m"),
            layer=Layer.E,
            source="ccc",
            county_fips=fips,
            source_url=first_source_url(row),
            source_record_id=sid,
            grievance=grievances,
            stance=stance,
            referent=referent,
            confidence=conf,
            classifier_version=CLASSIFIER_VERSION,
            title=title,
            summary=summary,
            raw_payload_path=RAW_RELATIVE,
            ingested_at=ingested_at,
        )
    except ValueError as exc:
        flags["skip_reason"] = f"event_validation:{exc}"
        return None, flags

    return ev, flags


def event_to_jsonable(ev: Event) -> dict[str, Any]:
    d = asdict(ev)
    d["event_date"] = ev.event_date.isoformat()
    d["layer"] = ev.layer.value
    d["stance"] = ev.stance.value if ev.stance else None
    d["referent"] = ev.referent.value if ev.referent else None
    d["grievance"] = [g.value for g in ev.grievance]
    if ev.ingested_at is not None:
        d["ingested_at"] = ev.ingested_at.isoformat()
    return d


def write_events_jsonl(path: Path, events: Iterable[Event]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(event_to_jsonable(ev), ensure_ascii=False) + "\n")
            n += 1
    return n


def write_events_csv(path: Path, events: list[Event]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "event_id",
        "county_fips",
        "state",
        "event_date",
        "event_month",
        "layer",
        "source",
        "source_url",
        "source_record_id",
        "grievance",
        "stance",
        "referent",
        "confidence",
        "classifier_version",
        "title",
        "summary",
        "raw_payload_path",
        "ingested_at",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
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


def build_panel_rows(events: list[Event]) -> list[dict[str, Any]]:
    """Thin panel: county_fips × month → n_mobilization (events with valid FIPS only)."""
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for ev in events:
        if not ev.county_fips:
            continue
        counts[(ev.county_fips, ev.state, ev.event_month)] += 1
    rows = [
        {
            "county_fips": fips,
            "state": state,
            "month": month,
            "n_mobilization": n,
            "taxonomy_version": TAXONOMY_VERSION,
            "filter_version": FILTER_VERSION,
        }
        for (fips, state, month), n in sorted(counts.items())
    ]
    return rows


def write_panel_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "county_fips",
        "state",
        "month",
        "n_mobilization",
        "taxonomy_version",
        "filter_version",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def transform(
    raw_path: Path = DEFAULT_RAW,
    *,
    events_jsonl: Path = OUT_EVENTS_JSONL,
    events_csv: Path = OUT_EVENTS_CSV,
    panel_csv: Path = OUT_PANEL_CSV,
    qa_json: Path = OUT_QA_JSON,
) -> dict[str, Any]:
    if not raw_path.exists():
        raise FileNotFoundError(
            f"CCC CSV not found at {raw_path}. Run: make fetch-ccc"
        )

    ingested_at = datetime.now(timezone.utc)
    total = 0
    matched_pre_guard = 0
    events: list[Event] = []
    missing_fips = 0
    skipped = Counter()
    by_state: Counter[str] = Counter()
    by_rule: Counter[str] = Counter()
    valence_among_matched: Counter[str] = Counter()

    with raw_path.open(newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            blob = row_text_blob(row)
            # Count pre-robot-guard for QA transparency
            raw_hits = [name for name, cre in _ALLOW if cre.search(blob)] if blob else []
            if raw_hits:
                matched_pre_guard += 1
            hits = match_allowlist(blob)
            if not hits:
                continue
            for h in hits:
                by_rule[h] += 1
            ev, flags = row_to_event(row, rule_hits=hits, ingested_at=ingested_at)
            if ev is None:
                skipped[flags.get("skip_reason", "unknown")] += 1
                continue
            if flags.get("missing_fips"):
                missing_fips += 1
            if flags.get("ccc_valence") is not None:
                valence_among_matched[str(flags["ccc_valence"])] += 1
            events.append(ev)
            by_state[ev.state] += 1

    # Dedupe by event_id (identical date/locality/state/title/claims)
    deduped: dict[str, Event] = {}
    for ev in events:
        deduped[ev.event_id] = ev
    events = list(deduped.values())
    events.sort(key=lambda e: (e.event_date, e.state, e.event_id))

    write_events_jsonl(events_jsonl, events)
    write_events_csv(events_csv, events)
    panel_rows = build_panel_rows(events)
    write_panel_csv(panel_csv, panel_rows)

    qa = {
        "filter_version": FILTER_VERSION,
        "classifier_version": CLASSIFIER_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "raw_path": str(raw_path.relative_to(ROOT)) if raw_path.is_relative_to(ROOT) else str(raw_path),
        "access_note": "CCC phase-3 public CSV already on disk; transform run 2026-09-16 PT",
        "total_ccc_rows": total,
        "matched_allowlist_rows": len(events),
        "matched_pre_robot_guard_rows": matched_pre_guard,
        "missing_fips_among_matched": missing_fips,
        "panel_rows": len(panel_rows),
        "panel_n_mobilization_sum": sum(r["n_mobilization"] for r in panel_rows),
        "by_state": dict(sorted(by_state.items())),
        "by_rule_hit": dict(by_rule.most_common()),
        "skipped": dict(skipped),
        "valence_among_matched": dict(valence_among_matched),
        "stance_policy": "default oppose for CCC protest/mobilization rows; valence not remapped in v0",
        "outputs": {
            "events_jsonl": str(events_jsonl.relative_to(ROOT)),
            "events_csv": str(events_csv.relative_to(ROOT)),
            "panel_csv": str(panel_csv.relative_to(ROOT)),
            "qa_json": str(qa_json.relative_to(ROOT)),
        },
        "rules_doc": "docs/filters/ccc_ai_keywords_v0.md",
        "generated_at_utc": ingested_at.isoformat(),
    }
    qa_json.parent.mkdir(parents=True, exist_ok=True)
    qa_json.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    return qa


def main() -> None:
    p = argparse.ArgumentParser(
        description="Transform CCC phase-3 CSV → AI/data-center-related events + panel"
    )
    p.add_argument(
        "--raw",
        type=Path,
        default=DEFAULT_RAW,
        help="Path to ccc-phase3-public.csv",
    )
    args = p.parse_args()
    qa = transform(raw_path=args.raw)
    print(f"filter_version={qa['filter_version']}")
    print(f"total_ccc_rows={qa['total_ccc_rows']}")
    print(f"matched_allowlist_rows={qa['matched_allowlist_rows']}")
    print(f"missing_fips_among_matched={qa['missing_fips_among_matched']}")
    print(f"panel_rows={qa['panel_rows']}")
    print(f"by_state={qa['by_state']}")
    print(f"by_rule_hit={qa['by_rule_hit']}")
    print(f"outputs={qa['outputs']}")


if __name__ == "__main__":
    main()
