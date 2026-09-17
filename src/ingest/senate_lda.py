"""Senate LDA.gov lobbying disclosures (free public REST API) — adjunct layer.

API (no key required for anonymous read; verified 2026-09-16 PT):
  https://lda.gov/api/v1/  (https://lda.senate.gov/api/ redirects here)
  Anonymous throttle: 15 req/min · registered key: 120/min (optional; not used)
  Docs/ToS: https://lda.gov/api/tos/ · https://lda.gov/api/redoc/v1/

v0 strategy (do not invent rows):
  1. Query filings by documented client_name seeds (partial match works).
  2. Deduplicate by filing_uuid; write raw JSONL under data/raw/senate_lda/.
  3. Apply lda_rules_v0 keyword filter → small processed sample + QA.
  4. Geo: use client.state (USPS) when present; county_fips always blank
     (federal LDA rarely carries county — QA note).

issue_code query param is documented in third-party OpenAPI mirrors but does
NOT filter on the live API (2026-09-16 PT probe) — do not rely on it.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ._download import ROOT, sha256_file, write_manifest

RAW_DIR = ROOT / "data" / "raw" / "senate_lda"
PROCESSED_DIR = ROOT / "data" / "processed" / "lobbying"
QA_DIR = ROOT / "data" / "processed" / "qa"
ACCESS_NOTE = RAW_DIR / "ACCESS.md"

API_BASE = "https://lda.gov/api/v1"
FILINGS_URL = f"{API_BASE}/filings/"
LEGACY_API_NOTE = "https://lda.senate.gov/api/ (301 → lda.gov)"
TOS_URL = "https://lda.gov/api/tos/"
REDOC_URL = "https://lda.gov/api/redoc/v1/"
USER_AGENT = "ai-backlash-tracker/0.1 (free-data; research; polite LDA sample)"

# Anonymous limit is 15/min — sleep ≥4s between calls.
DEFAULT_SLEEP_S = 4.2
DEFAULT_TIMEOUT = 60
PAGE_LIMIT = 25  # API max

FILTER_VERSION = "lda_rules_v0"
FILTER_DOC = "docs/filters/lda_ai_keywords_v0.md"

# API client_name seeds (partial match). Precision-oriented; documented in filter doc.
# These are QUERY seeds, not invented matches — empty seed results are kept as counts.
CLIENT_NAME_SEEDS: tuple[str, ...] = (
    "OpenAI",
    "Anthropic",
    "NVIDIA",
    "CoreWeave",
    "data center",
    "Equinix",
    "Digital Realty",
    "CyrusOne",
    "Vantage Data",
    "Semiconductor",
    "Taiwan Semiconductor",
    "Micron Technology",
    "Advanced Micro Devices",
    "GlobalFoundries",
    "Edison Electric",
    "American Electric Power",
    "Duke Energy",
    "Dominion Energy",
    "Southern Company",
    "NextEra Energy",
    "xAI",
)

# Years to intersect with each seed (keeps sample bounded + year counts meaningful).
DEFAULT_YEARS: tuple[int, ...] = (2023, 2024, 2025)

# Keyword allowlist applied client-side after fetch (precision over recall).
ALLOWLIST: list[tuple[str, str]] = [
    ("data_center", r"data[\s\-]?cent(?:er|re)s?"),
    ("datacenter", r"datacent(?:er|re)s?"),
    ("server_farm", r"server\s+farms?"),
    ("hyperscale", r"hyperscale"),
    ("artificial_intelligence", r"artificial\s+intelligence"),
    ("agi", r"artificial\s+general\s+intelligence|\bAGIs?\b"),
    ("generative_ai", r"generative\s+AI"),
    ("chatgpt", r"chatgpt"),
    ("openai", r"openai"),
    ("anthropic", r"anthropic"),
    ("machine_learning", r"\bmachine\s+learning\b"),
    ("llm", r"\bLLMs?\b"),
    ("gpu", r"\bGPUs?\b"),
    ("ai_word", r"\bAI\b"),
    ("semiconductor", r"semiconductor"),
    ("chipmaker", r"\bchip\s*maker|\bfab(?:rication)?\b|\bfoundry\b"),
    ("nvidia", r"nvidia"),
    ("coreweave", r"coreweave"),
    ("electric_utility", r"electric\s+utilit"),
    ("power_utility", r"(?:\belectric\b|\bpower\b).{0,40}\butilit"),
    ("data_center_operator", r"\bequinix\b|\bdigital\s+realty\b|\bcyrusone\b|\bvantage\s+data"),
]

_ALLOW_RE = [(n, re.compile(p, re.I)) for n, p in ALLOWLIST]

# Explicit non-match: bare Big Tech client names alone without allowlist term.
# (Seeds may still pull them via other seeds; keyword filter drops unless AI/DC/etc.)


def _write_access_note() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ACCESS_NOTE.write_text(
        "\n".join(
            [
                "# Senate LDA (Lobbying Disclosure Act) access",
                "",
                f"- API root: {API_BASE}/",
                f"- Legacy host: {LEGACY_API_NOTE}",
                f"- ToS: {TOS_URL}",
                f"- Redoc: {REDOC_URL}",
                "- Auth: **none required** for public read (anonymous).",
                "- Rate limits (ToS): anonymous **15/min**; API key **120/min** (optional).",
                "- Bulk XML alternate: https://www.senate.gov/legislative/lobbyingdisc.htm",
                "- Cite access date; Senate OPR cannot vouch for downstream analyses (ToS).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return ACCESS_NOTE


def _api_get(url: str, *, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def _filings_query(**params: Any) -> str:
    q = {k: v for k, v in params.items() if v is not None}
    return FILINGS_URL + "?" + urllib.parse.urlencode(q)


def fetch_filings_for_query(
    *,
    client_name: str,
    filing_year: Optional[int],
    sleep_s: float,
    max_pages: Optional[int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Paginate filings for one client_name (+ optional year). Returns (results, meta)."""
    page = 1
    all_rows: list[dict[str, Any]] = []
    first_count: Optional[int] = None
    pages_fetched = 0
    error: Optional[str] = None

    while True:
        if max_pages is not None and pages_fetched >= max_pages:
            break
        url = _filings_query(
            client_name=client_name,
            filing_year=filing_year,
            page=page,
            format="json",
        )
        try:
            payload = _api_get(url)
        except urllib.error.HTTPError as exc:
            error = f"HTTP {exc.code}: {exc.reason}"
            break
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            break

        if first_count is None:
            first_count = payload.get("count")
        results = payload.get("results") or []
        if not isinstance(results, list):
            error = "unexpected results type"
            break
        all_rows.extend(results)
        pages_fetched += 1
        nxt = payload.get("next")
        if not nxt or not results:
            break
        page += 1
        time.sleep(sleep_s)

    meta = {
        "client_name": client_name,
        "filing_year": filing_year,
        "api_count": first_count,
        "pages_fetched": pages_fetched,
        "rows_returned": len(all_rows),
        "error": error,
        "truncated": not error and (max_pages is None or (first_count or 0) <= len(all_rows)),
    }
    return all_rows, meta


def filing_text_blob(rec: dict[str, Any]) -> str:
    client = rec.get("client") or {}
    parts = [
        str(client.get("name") or ""),
        str(client.get("general_description") or ""),
        str((rec.get("registrant") or {}).get("name") or ""),
        str((rec.get("registrant") or {}).get("description") or ""),
    ]
    for act in rec.get("lobbying_activities") or []:
        if not isinstance(act, dict):
            continue
        parts.append(str(act.get("general_issue_code_display") or ""))
        parts.append(str(act.get("description") or ""))
    return " ".join(parts)


def keyword_hits(text: str) -> list[str]:
    hits: list[str] = []
    for name, cre in _ALLOW_RE:
        if cre.search(text):
            hits.append(name)
    return hits


def usps_state(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip().upper()
    if len(s) == 2 and s.isalpha():
        return s
    return None


def filing_month(rec: dict[str, Any]) -> Optional[str]:
    """Prefer dt_posted → YYYY-MM; else filing_year alone is not a month."""
    dt = rec.get("dt_posted")
    if isinstance(dt, str) and len(dt) >= 7:
        # e.g. 2024-01-02T10:13:41-05:00
        try:
            # Handle timezone offsets without depending on dateutil
            iso = dt.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(iso)
            return f"{parsed.year:04d}-{parsed.month:02d}"
        except ValueError:
            if re.match(r"^\d{4}-\d{2}", dt):
                return dt[:7]
    year = rec.get("filing_year")
    period = str(rec.get("filing_period") or "").lower()
    # Coarse quarter midpoints only when dt_posted missing — documented as approximate.
    quarter_month = {
        "first_quarter": "02",
        "second_quarter": "05",
        "third_quarter": "08",
        "fourth_quarter": "11",
        "mid_year": "06",
        "year_end": "12",
        "first_semi_annual": "03",
        "second_semi_annual": "09",
    }
    if isinstance(year, int) and period in quarter_month:
        return f"{year:04d}-{quarter_month[period]}"
    return None


def flatten_filing(rec: dict[str, Any], *, seed: str, hits: list[str]) -> dict[str, Any]:
    client = rec.get("client") or {}
    registrant = rec.get("registrant") or {}
    activities = rec.get("lobbying_activities") or []
    issue_codes = sorted(
        {
            str(a.get("general_issue_code"))
            for a in activities
            if isinstance(a, dict) and a.get("general_issue_code")
        }
    )
    state = usps_state(client.get("state")) or usps_state(client.get("ppb_state"))
    month = filing_month(rec)
    return {
        "filing_uuid": rec.get("filing_uuid"),
        "filing_year": rec.get("filing_year"),
        "filing_period": rec.get("filing_period"),
        "filing_type": rec.get("filing_type"),
        "filing_type_display": rec.get("filing_type_display"),
        "dt_posted": rec.get("dt_posted"),
        "event_month": month,
        "state": state or "",
        "county_fips": "",  # federal LDA — intentionally blank
        "client_id": client.get("id") or client.get("client_id"),
        "client_name": client.get("name"),
        "client_description": client.get("general_description"),
        "registrant_id": registrant.get("id"),
        "registrant_name": registrant.get("name"),
        "income": rec.get("income"),
        "expenses": rec.get("expenses"),
        "issue_codes": "|".join(issue_codes),
        "n_activities": len(activities) if isinstance(activities, list) else 0,
        "keyword_hits": "|".join(hits),
        "matched_seed": seed,
        "source_url": rec.get("filing_document_url") or rec.get("url"),
        "filter_version": FILTER_VERSION,
    }


def run(
    *,
    years: tuple[int, ...],
    seeds: tuple[str, ...],
    sleep_s: float,
    max_pages_per_query: Optional[int],
    force: bool,
) -> dict[str, Any]:
    _write_access_note()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = RAW_DIR / "filings_sample_v0.jsonl"
    meta_path = RAW_DIR / "fetch_meta_v0.json"
    sample_csv = PROCESSED_DIR / "senate_lda_ai_related_v0.csv"
    sample_jsonl = PROCESSED_DIR / "senate_lda_ai_related_v0.jsonl"
    qa_path = QA_DIR / "senate_lda_ai_related_v0_qa.json"

    if raw_path.exists() and not force:
        print(f"raw present ({raw_path}); use --force to re-fetch")
        filings_by_uuid: dict[str, dict[str, Any]] = {}
        seed_by_uuid: dict[str, str] = {}
        with raw_path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                uid = obj.get("filing_uuid")
                if not uid:
                    continue
                filings_by_uuid[uid] = obj
                seed_by_uuid[uid] = obj.get("_matched_seed") or seed_by_uuid.get(uid, "")
        query_metas: list[dict[str, Any]] = []
        if meta_path.exists():
            query_metas = json.loads(meta_path.read_text(encoding="utf-8")).get("queries") or []
    else:
        filings_by_uuid = {}
        seed_by_uuid = {}
        query_metas = []
        first = True
        for seed in seeds:
            for year in years:
                if not first:
                    time.sleep(sleep_s)
                first = False
                print(f"fetch client_name={seed!r} year={year} …")
                rows, meta = fetch_filings_for_query(
                    client_name=seed,
                    filing_year=year,
                    sleep_s=sleep_s,
                    max_pages=max_pages_per_query,
                )
                query_metas.append(meta)
                print(
                    f"  api_count={meta.get('api_count')} "
                    f"rows={meta.get('rows_returned')} pages={meta.get('pages_fetched')} "
                    f"err={meta.get('error')}"
                )
                for rec in rows:
                    uid = rec.get("filing_uuid")
                    if not uid:
                        continue
                    if uid not in filings_by_uuid:
                        filings_by_uuid[uid] = rec
                        seed_by_uuid[uid] = seed
                    # keep first seed; note overlaps in QA later

        with raw_path.open("w", encoding="utf-8") as fh:
            for uid, rec in filings_by_uuid.items():
                out = dict(rec)
                out["_matched_seed"] = seed_by_uuid.get(uid, "")
                fh.write(json.dumps(out, ensure_ascii=False) + "\n")

        meta_payload = {
            "filter_version": FILTER_VERSION,
            "api_base": API_BASE,
            "auth": "anonymous (no API key)",
            "rate_limit_note": "anonymous 15/min; slept between requests",
            "sleep_s": sleep_s,
            "years": list(years),
            "client_name_seeds": list(seeds),
            "n_unique_filings": len(filings_by_uuid),
            "queries": query_metas,
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "issue_code_note": (
                "Live API ignores issue_code / general_issue_code query params "
                "(probe 2026-09-16 PT); v0 uses client_name seeds only."
            ),
        }
        meta_path.write_text(json.dumps(meta_payload, indent=2) + "\n", encoding="utf-8")

    # Keyword filter → processed sample
    hit_rows: list[dict[str, Any]] = []
    year_counts_all: Counter[str] = Counter()
    year_counts_hits: Counter[str] = Counter()
    state_counts_hits: Counter[str] = Counter()
    seed_counts: Counter[str] = Counter()
    missing_state = 0
    month_ok = 0
    month_missing = 0

    for uid, rec in filings_by_uuid.items():
        year = rec.get("filing_year")
        year_key = str(year) if year is not None else "(blank)"
        year_counts_all[year_key] += 1
        seed = seed_by_uuid.get(uid) or rec.get("_matched_seed") or ""
        seed_counts[seed] += 1
        blob = filing_text_blob(rec)
        hits = keyword_hits(blob)
        if not hits:
            continue
        flat = flatten_filing(rec, seed=seed, hits=hits)
        hit_rows.append(flat)
        year_counts_hits[year_key] += 1
        st = flat.get("state") or "(blank)"
        state_counts_hits[st] += 1
        if not flat.get("state"):
            missing_state += 1
        if flat.get("event_month"):
            month_ok += 1
        else:
            month_missing += 1

    # Stable sort
    hit_rows.sort(key=lambda r: (r.get("filing_year") or 0, r.get("dt_posted") or "", r.get("filing_uuid") or ""))

    fieldnames = [
        "filing_uuid",
        "filing_year",
        "filing_period",
        "filing_type",
        "filing_type_display",
        "dt_posted",
        "event_month",
        "state",
        "county_fips",
        "client_id",
        "client_name",
        "client_description",
        "registrant_id",
        "registrant_name",
        "income",
        "expenses",
        "issue_codes",
        "n_activities",
        "keyword_hits",
        "matched_seed",
        "source_url",
        "filter_version",
    ]
    with sample_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for row in hit_rows:
            w.writerow(row)
    with sample_jsonl.open("w", encoding="utf-8") as fh:
        for row in hit_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    qa = {
        "source_id": "senate_lda",
        "layer": "lobbying_adjunct",
        "filter_version": FILTER_VERSION,
        "filter_doc": FILTER_DOC,
        "api_base": API_BASE,
        "auth": "anonymous_no_key",
        "rate_limit": "anonymous_15_per_min",
        "n_raw_unique_filings": len(filings_by_uuid),
        "n_keyword_hit_filings": len(hit_rows),
        "counts_by_year_raw": dict(sorted(year_counts_all.items())),
        "counts_by_year_keyword_hits": dict(sorted(year_counts_hits.items())),
        "counts_by_state_keyword_hits": dict(sorted(state_counts_hits.items(), key=lambda kv: (-kv[1], kv[0]))),
        "counts_by_seed_raw": dict(sorted(seed_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "geo": {
            "county_fips": "always_blank",
            "note": (
                "Federal LDA filings are national disclosures; client.state / "
                "client.ppb_state used when USPS-2 present. No county_fips invented."
            ),
            "missing_state_among_hits": missing_state,
            "event_month_ok": month_ok,
            "event_month_missing": month_missing,
        },
        "raw_path": str(raw_path.relative_to(ROOT)),
        "processed_csv": str(sample_csv.relative_to(ROOT)),
        "processed_jsonl": str(sample_jsonl.relative_to(ROOT)),
        "client_name_seeds": list(seeds),
        "years": list(years),
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    qa_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")

    # Manifests
    write_manifest(
        "senate_lda",
        {
            "source_id": "senate_lda",
            "layer": "lobbying_adjunct",
            "url": FILINGS_URL,
            "api_base": API_BASE,
            "legacy_api": "https://lda.senate.gov/api/",
            "tos": TOS_URL,
            "redoc": REDOC_URL,
            "path": str(raw_path.relative_to(ROOT)),
            "bytes": raw_path.stat().st_size if raw_path.exists() else 0,
            "sha256": sha256_file(raw_path) if raw_path.exists() else None,
            "status": "downloaded",
            "auth": "anonymous (no API key required for public read)",
            "rate_limit_note": "anonymous 15/min; key optional 120/min — this ingest uses anonymous + sleep",
            "license_note": (
                "US Senate LDA public disclosures; cite access date; "
                "Senate OPR cannot vouch for analyses after retrieval (ToS)"
            ),
            "notes": (
                "v0 sample: client_name seed queries × years, deduped by filing_uuid; "
                f"keyword filter {FILTER_VERSION}. issue_code API filter ineffective on probe. "
                "county_fips blank (federal). Bulk XML alternate documented in ACCESS.md."
            ),
            "filter_version": FILTER_VERSION,
            "filter_doc": FILTER_DOC,
            "n_unique_filings": len(filings_by_uuid),
            "n_keyword_hit_filings": len(hit_rows),
            "years": list(years),
            "client_name_seeds": list(seeds),
            "meta_path": str(meta_path.relative_to(ROOT)),
            "qa_path": str(qa_path.relative_to(ROOT)),
            "processed_csv": str(sample_csv.relative_to(ROOT)),
        },
    )

    print(
        f"done: raw={len(filings_by_uuid)} unique filings; "
        f"keyword hits={len(hit_rows)}; qa={qa_path}"
    )
    return qa


def main(argv: Optional[list[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Fetch Senate LDA filings sample (free API)")
    p.add_argument("--force", action="store_true", help="Re-fetch even if raw JSONL exists")
    p.add_argument(
        "--sleep",
        type=float,
        default=DEFAULT_SLEEP_S,
        help=f"Seconds between API calls (default {DEFAULT_SLEEP_S} for ≤15/min)",
    )
    p.add_argument(
        "--years",
        type=str,
        default=",".join(str(y) for y in DEFAULT_YEARS),
        help="Comma-separated filing years (default 2023,2024,2025)",
    )
    p.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional cap on pages per seed×year query (25 rows/page)",
    )
    p.add_argument(
        "--seeds",
        type=str,
        default=None,
        help="Comma-separated client_name seeds (default: built-in lda_rules_v0 list)",
    )
    args = p.parse_args(argv)
    years = tuple(int(x.strip()) for x in args.years.split(",") if x.strip())
    seeds: tuple[str, ...]
    if args.seeds:
        seeds = tuple(s.strip() for s in args.seeds.split(",") if s.strip())
    else:
        seeds = CLIENT_NAME_SEEDS
    run(
        years=years,
        seeds=seeds,
        sleep_s=args.sleep,
        max_pages_per_query=args.max_pages,
        force=args.force,
    )


if __name__ == "__main__":
    main()
