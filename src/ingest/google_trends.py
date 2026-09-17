"""Layer F — Google Trends state-level free pilot (no paid API).

Source: https://trends.google.com/trends/
Client: community `pytrends` only (optional install). **No paid Trends API.**

Policy:
  - Tiny keyword list (≤5) documented in docs/filters/google_trends_keywords_v0.md
  - Strict sleep/backoff between calls; never hammer endpoints
  - State-level monthly series when Google allows; county_fips always blank
  - DMA→county crosswalk deferred (documented, not invented)
  - On 429 / CAPTCHA / client errors: write ACCESS.md + blocked manifest/QA —
    **do not invent interest index numbers**
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ._download import ROOT, sha256_file, write_manifest

RAW_DIR = ROOT / "data" / "raw" / "trends"
QA_DIR = ROOT / "data" / "processed" / "qa"
ACCESS_NOTE = RAW_DIR / "ACCESS.md"
RAW_CSV = RAW_DIR / "google_trends_state_month_v0.csv"
QA_JSON = QA_DIR / "google_trends_state_month_v0_qa.json"

TRENDS_HOME = "https://trends.google.com/trends/"
FILTER_VERSION = "trends_keywords_v0"
FILTER_DOC = "docs/filters/google_trends_keywords_v0.md"
USER_AGENT = "ai-backlash-tracker/0.1 (free-data research; polite Trends pilot)"

# ≤5 keywords — keep in sync with filter doc.
KEYWORDS: tuple[str, ...] = (
    "data center",
    "ChatGPT",
    "artificial intelligence",
)

# Pilot states (USPS). Full 50+DC is available via --all-states but needs long wall time.
PILOT_STATES: tuple[str, ...] = ("CA", "TX", "VA", "NY", "GA")

# USPS → pytrends geo code
_USPS_TO_GEO: dict[str, str] = {
    "AL": "US-AL",
    "AK": "US-AK",
    "AZ": "US-AZ",
    "AR": "US-AR",
    "CA": "US-CA",
    "CO": "US-CO",
    "CT": "US-CT",
    "DE": "US-DE",
    "DC": "US-DC",
    "FL": "US-FL",
    "GA": "US-GA",
    "HI": "US-HI",
    "ID": "US-ID",
    "IL": "US-IL",
    "IN": "US-IN",
    "IA": "US-IA",
    "KS": "US-KS",
    "KY": "US-KY",
    "LA": "US-LA",
    "ME": "US-ME",
    "MD": "US-MD",
    "MA": "US-MA",
    "MI": "US-MI",
    "MN": "US-MN",
    "MS": "US-MS",
    "MO": "US-MO",
    "MT": "US-MT",
    "NE": "US-NE",
    "NV": "US-NV",
    "NH": "US-NH",
    "NJ": "US-NJ",
    "NM": "US-NM",
    "NY": "US-NY",
    "NC": "US-NC",
    "ND": "US-ND",
    "OH": "US-OH",
    "OK": "US-OK",
    "OR": "US-OR",
    "PA": "US-PA",
    "RI": "US-RI",
    "SC": "US-SC",
    "SD": "US-SD",
    "TN": "US-TN",
    "TX": "US-TX",
    "UT": "US-UT",
    "VT": "US-VT",
    "VA": "US-VA",
    "WA": "US-WA",
    "WV": "US-WV",
    "WI": "US-WI",
    "WY": "US-WY",
}

DEFAULT_TIMEFRAME = "2023-01-01 2025-12-31"
DEFAULT_SLEEP_S = 20.0  # strict polite gap between pytrends calls
DEFAULT_BACKOFF_S = 60.0  # extra wait after 429 before giving up / retry once


CSV_FIELDS = (
    "state",
    "county_fips",
    "month",
    "keyword",
    "interest",
    "geo_code",
    "timeframe",
    "filter_version",
    "retrieved_at_utc",
)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_access_note(
    *,
    status: str,
    homepage_http: Optional[int],
    blocker: str,
    detail: str,
) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Google Trends access (Layer F free pilot)",
        "",
        f"- Site: {TRENDS_HOME}",
        "- **No paid API.** Free path only: browser export or community `pytrends`.",
        f"- Filter: `{FILTER_VERSION}` — see `{FILTER_DOC}`",
        f"- Keywords (≤5): {', '.join(repr(k) for k in KEYWORDS)}",
        "- Grain: **state × month** when pulls succeed; **`county_fips` always blank**.",
        "- DMA→county: **deferred** (native Trends geo is often DMA/metro or state).",
        "- Relative index only — series not comparable across pulls without a shared anchor.",
        "",
        f"## Probe status ({_now_utc()} Z / local PT same calendar day)",
        "",
        f"- Manifest status: **`{status}`**",
        f"- Trends homepage HTTP: `{homepage_http}`",
        f"- Blocker: {blocker or '(none)'}",
        "",
        "## Detail",
        "",
        detail,
        "",
        "## Policy",
        "",
        "- Do **not** invent interest index numbers when Google blocks or returns empty.",
        "- Raw CSV under `data/raw/trends/` is gitignored; commit manifests + QA + this note.",
        "- Re-run `make fetch-google-trends` later with longer `--sleep` if rate-limited.",
        "",
    ]
    ACCESS_NOTE.write_text("\n".join(lines), encoding="utf-8")
    return ACCESS_NOTE


def _probe_homepage(timeout: int = 30) -> tuple[Optional[int], str]:
    req = urllib.request.Request(
        TRENDS_HOME,
        headers={"User-Agent": USER_AGENT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
            body = resp.read(256)
            note = f"GET {TRENDS_HOME} → {code}; body_prefix_bytes={len(body)}"
            return int(code), note
    except urllib.error.HTTPError as exc:
        return int(exc.code), f"HTTPError {exc.code}: {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def _import_pytrends():
    try:
        from pytrends.request import TrendReq  # type: ignore

        return TrendReq
    except ImportError as exc:
        raise RuntimeError(
            "pytrends not installed. Free client only: "
            "`pip install pytrends` (optional; listed commented in requirements.txt)."
        ) from exc


def _make_trend_req(TrendReq: Any) -> Any:
    """Construct TrendReq, working around urllib3 Retry API drift."""
    try:
        return TrendReq(
            hl="en-US",
            tz=360,
            timeout=(10, 30),
            retries=0,
            requests_args={"headers": {"User-Agent": USER_AGENT}},
        )
    except TypeError:
        # Older/newer pytrends signatures vary; minimal ctor.
        return TrendReq(hl="en-US", tz=360)


def _monthly_rows_from_iot(
    df: Any,
    *,
    keyword: str,
    state: str,
    geo_code: str,
    timeframe: str,
    retrieved_at: str,
) -> list[dict[str, Any]]:
    """Aggregate pytrends interest_over_time (often weekly) → monthly mean.

    Never fabricates values: empty/missing → no rows for that month.
    """
    if df is None or getattr(df, "empty", True):
        return []
    if keyword not in df.columns:
        return []
    # Drop isPartial column if present
    series = df[keyword].copy()
    if hasattr(series.index, "to_period"):
        monthly = series.groupby(series.index.to_period("M")).mean()
    else:
        return []
    rows: list[dict[str, Any]] = []
    for period, value in monthly.items():
        if value is None:
            continue
        try:
            interest = float(value)
        except (TypeError, ValueError):
            continue
        if interest != interest:  # NaN
            continue
        month = str(period)  # YYYY-MM
        rows.append(
            {
                "state": state,
                "county_fips": "",
                "month": month,
                "keyword": keyword,
                "interest": round(interest, 4),
                "geo_code": geo_code,
                "timeframe": timeframe,
                "filter_version": FILTER_VERSION,
                "retrieved_at_utc": retrieved_at,
            }
        )
    return rows


def _fetch_state_keyword(
    pt: Any,
    *,
    keyword: str,
    state: str,
    timeframe: str,
    sleep_s: float,
) -> list[dict[str, Any]]:
    geo = _USPS_TO_GEO[state]
    # Polite gap before each call (including the first after homepage probe).
    time.sleep(max(0.0, sleep_s))
    pt.build_payload([keyword], cat=0, timeframe=timeframe, geo=geo, gprop="")
    df = pt.interest_over_time()
    return _monthly_rows_from_iot(
        df,
        keyword=keyword,
        state=state,
        geo_code=geo,
        timeframe=timeframe,
        retrieved_at=_now_utc(),
    )


def _write_csv(rows: list[dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in CSV_FIELDS})
    return path


def _write_qa(payload: dict[str, Any]) -> Path:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    QA_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return QA_JSON


def fetch(
    *,
    states: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    sleep_s: float = DEFAULT_SLEEP_S,
    backoff_s: float = DEFAULT_BACKOFF_S,
    probe_only: bool = False,
    skip_network: bool = False,
) -> dict[str, Any]:
    """Run Trends pilot. Returns QA-shaped summary (also written to disk)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    states = states or list(PILOT_STATES)
    keywords = keywords or list(KEYWORDS)
    for s in states:
        if s not in _USPS_TO_GEO:
            raise ValueError(f"Unknown USPS state code: {s}")
    if len(keywords) > 5:
        raise ValueError("Keyword list must be ≤5 for this free pilot.")

    homepage_http: Optional[int] = None
    homepage_note = "skipped"
    if not skip_network:
        homepage_http, homepage_note = _probe_homepage()

    status = "documented_only"
    blocker = ""
    detail_parts = [homepage_note]
    rows: list[dict[str, Any]] = []
    calls_attempted = 0
    calls_ok = 0
    last_error = ""

    if skip_network:
        status = "documented_only"
        blocker = "skip_network=True (docs/stub only; no live Trends calls)"
        detail_parts.append(blocker)
    else:
        try:
            TrendReq = _import_pytrends()
            pt = _make_trend_req(TrendReq)
            work = [(kw, st) for kw in keywords for st in states]
            if probe_only:
                work = work[:1]
            for kw, st in work:
                calls_attempted += 1
                try:
                    part = _fetch_state_keyword(
                        pt,
                        keyword=kw,
                        state=st,
                        timeframe=timeframe,
                        sleep_s=sleep_s,
                    )
                    rows.extend(part)
                    calls_ok += 1
                except Exception as exc:  # noqa: BLE001 — document blockers
                    last_error = f"{type(exc).__name__}: {exc}"
                    detail_parts.append(
                        f"call keyword={kw!r} state={st} failed: {last_error}"
                    )
                    # One polite backoff retry for rate limits
                    err_l = last_error.lower()
                    if "429" in err_l or "too many" in err_l or "rate" in err_l:
                        time.sleep(max(0.0, backoff_s))
                        try:
                            calls_attempted += 1
                            part = _fetch_state_keyword(
                                pt,
                                keyword=kw,
                                state=st,
                                timeframe=timeframe,
                                sleep_s=0.0,  # already waited backoff
                            )
                            rows.extend(part)
                            calls_ok += 1
                            last_error = ""
                            continue
                        except Exception as exc2:  # noqa: BLE001
                            last_error = f"{type(exc2).__name__}: {exc2}"
                            detail_parts.append(f"retry failed: {last_error}")
                    # Stop further calls after hard block to stay polite
                    blocker = last_error
                    status = "blocked"
                    break
            else:
                if calls_ok > 0 and rows:
                    status = "downloaded"
                elif calls_ok > 0 and not rows:
                    status = "blocked"
                    blocker = blocker or "pytrends returned empty frames (no invented rows)"
                else:
                    status = "blocked"
                    blocker = blocker or last_error or "no successful Trends calls"
        except Exception as exc:  # noqa: BLE001
            status = "blocked"
            blocker = f"{type(exc).__name__}: {exc}"
            detail_parts.append(blocker)

    # Never write fabricated interest rows. Empty CSV header-only if blocked.
    csv_path = _write_csv(rows, RAW_CSV)
    csv_sha = sha256_file(csv_path) if csv_path.exists() else None
    csv_bytes = csv_path.stat().st_size if csv_path.exists() else 0

    detail = "\n".join(f"- {p}" for p in detail_parts if p)
    if status == "downloaded":
        detail += (
            f"\n- Wrote {len(rows)} real monthly rows to `{csv_path.relative_to(ROOT)}`."
        )
    else:
        detail += (
            "\n- **No Trends index numbers invented.** "
            f"CSV is header-only or empty of interest rows ({len(rows)} data rows)."
        )

    _write_access_note(
        status=status,
        homepage_http=homepage_http,
        blocker=blocker or "(none — see detail)",
        detail=detail,
    )

    by_state: dict[str, int] = {}
    by_keyword: dict[str, int] = {}
    for r in rows:
        by_state[r["state"]] = by_state.get(r["state"], 0) + 1
        by_keyword[r["keyword"]] = by_keyword.get(r["keyword"], 0) + 1

    qa = {
        "source_id": "google_trends",
        "layer": "F",
        "filter_version": FILTER_VERSION,
        "filter_doc": FILTER_DOC,
        "status": status,
        "blocker": blocker or None,
        "homepage_http": homepage_http,
        "trends_home": TRENDS_HOME,
        "paid_api": False,
        "client": "pytrends (optional free community library)",
        "keywords": list(keywords),
        "states_requested": list(states),
        "timeframe": timeframe,
        "sleep_s": sleep_s,
        "backoff_s": backoff_s,
        "probe_only": probe_only,
        "calls_attempted": calls_attempted,
        "calls_ok": calls_ok,
        "n_rows": len(rows),
        "by_state": by_state,
        "by_keyword": by_keyword,
        "geo": {
            "grain": "state_month",
            "county_fips": "always_blank",
            "dma_to_county": "deferred",
            "note": (
                "Native Trends geography is DMA/metro or state. "
                "County panel requires an explicit DMA→county crosswalk — not shipped."
            ),
        },
        "raw_csv": str(csv_path.relative_to(ROOT)),
        "raw_bytes": csv_bytes,
        "raw_sha256": csv_sha,
        "access_note": str(ACCESS_NOTE.relative_to(ROOT)),
        "invented_values": False,
        "recorded_at_utc": _now_utc(),
    }
    _write_qa(qa)

    write_manifest(
        "google_trends",
        {
            "source_id": "google_trends",
            "layer": "F",
            "url": TRENDS_HOME,
            "path": str(csv_path.relative_to(ROOT)),
            "bytes": csv_bytes,
            "sha256": csv_sha,
            "status": status,
            "blocker": blocker or None,
            "license_note": (
                "Google Terms of Service; Trends is a relative index "
                "(not absolute volume). Free scrape/export only — no paid API."
            ),
            "notes": (
                f"{FILTER_VERSION}: state×month pilot; county_fips blank; "
                "DMA→county deferred. Strict backoff between pytrends calls. "
                "No invented interest numbers when blocked."
            ),
            "filter_version": FILTER_VERSION,
            "filter_doc": FILTER_DOC,
            "keywords": list(keywords),
            "states_requested": list(states),
            "timeframe": timeframe,
            "n_rows": len(rows),
            "qa_path": str(QA_JSON.relative_to(ROOT)),
            "local_access_note": str(ACCESS_NOTE.relative_to(ROOT)),
            "paid_api": False,
        },
    )
    return qa


def main() -> None:
    p = argparse.ArgumentParser(
        description="Layer F Google Trends state-level free pilot (pytrends; no paid API)."
    )
    p.add_argument(
        "--states",
        default=",".join(PILOT_STATES),
        help=f"Comma-separated USPS codes (default pilot: {','.join(PILOT_STATES)})",
    )
    p.add_argument(
        "--all-states",
        action="store_true",
        help="Use all 50 states + DC (slow; needs long --sleep)",
    )
    p.add_argument(
        "--keywords",
        default=",".join(KEYWORDS),
        help="Comma-separated keywords (≤5)",
    )
    p.add_argument("--timeframe", default=DEFAULT_TIMEFRAME)
    p.add_argument(
        "--sleep",
        type=float,
        default=DEFAULT_SLEEP_S,
        help="Seconds between pytrends calls (strict backoff)",
    )
    p.add_argument(
        "--backoff",
        type=float,
        default=DEFAULT_BACKOFF_S,
        help="Extra seconds after a 429 before one retry",
    )
    p.add_argument(
        "--probe-only",
        action="store_true",
        help="Single (keyword, state) call only — access check",
    )
    p.add_argument(
        "--skip-network",
        action="store_true",
        help="Write docs/manifest/QA stub without calling Google",
    )
    args = p.parse_args()
    if args.all_states:
        states = list(_USPS_TO_GEO.keys())
    else:
        states = [s.strip().upper() for s in args.states.split(",") if s.strip()]
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    qa = fetch(
        states=states,
        keywords=keywords,
        timeframe=args.timeframe,
        sleep_s=args.sleep,
        backoff_s=args.backoff,
        probe_only=args.probe_only,
        skip_network=args.skip_network,
    )
    print(f"status={qa['status']}")
    print(f"blocker={qa.get('blocker')}")
    print(f"n_rows={qa['n_rows']} calls_ok={qa['calls_ok']}/{qa['calls_attempted']}")
    print(f"raw={qa['raw_csv']}")
    print(f"qa={QA_JSON.relative_to(ROOT)}")
    print(f"access={qa['access_note']}")


if __name__ == "__main__":
    main()
