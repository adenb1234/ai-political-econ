"""Layer E complement — Cornell–Illinois Labor Action Tracker (free).

Preferred free file: GitHub Pages deploy of labor_actions.json
  https://striketracker.ilr.cornell.edu/labor_actions.json

Also pulls Zenodo CC-BY snapshot Labor-prod.xlsx when reachable:
  DOI 10.5281/zenodo.16457619

Official email-for-spreadsheet path is documented only (not fetched).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ._download import ROOT, sha256_file, try_download, write_manifest

RAW_DIR = ROOT / "data" / "raw" / "labor_action"
PAGES_JSON_URL = "https://striketracker.ilr.cornell.edu/labor_actions.json"
ZENODO_DOI = "10.5281/zenodo.16457619"
ZENODO_XLSX_URL = (
    "https://zenodo.org/api/records/16457619/files/Labor-prod.xlsx/content"
)
PROJECT_PAGE = (
    "https://www.ilr.cornell.edu/faculty-and-research/labor-action-tracker"
)
MAP_SITE = "https://striketracker.ilr.cornell.edu/"
GITHUB_REPO = "https://github.com/ilrWebServices/StrikeSiteTracker"

DEST_JSON = RAW_DIR / "labor_actions.json"
DEST_XLSX = RAW_DIR / "Labor-prod.xlsx"
ACCESS_NOTE = RAW_DIR / "ACCESS.md"


def _write_access_note() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not ACCESS_NOTE.exists():
        ACCESS_NOTE.write_text(
            "\n".join(
                [
                    "# Labor Action Tracker access",
                    "",
                    f"- Map: {MAP_SITE}",
                    f"- Pages JSON: {PAGES_JSON_URL}",
                    f"- Zenodo: https://doi.org/{ZENODO_DOI}",
                    "- Email spreadsheet: Johnnie Kallas jkallas@illinois.edu (not auto-fetched).",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    return ACCESS_NOTE


def _summarize_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"record_type": type(data).__name__, "n_records": None}
    n_locs = 0
    action_types: dict[str, int] = {}
    for rec in data.values():
        if not isinstance(rec, dict):
            continue
        locs = rec.get("locations") or []
        if isinstance(locs, list):
            n_locs += len(locs)
        at = str(rec.get("Action_type") or "").strip() or "(blank)"
        action_types[at] = action_types.get(at, 0) + 1
    return {
        "n_actions": len(data),
        "n_locations": n_locs,
        "action_type_counts": dict(sorted(action_types.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def fetch_pages_json(force: bool = False) -> tuple[bool, Path]:
    if DEST_JSON.exists() and not force:
        print(f"already present: {DEST_JSON} ({DEST_JSON.stat().st_size} bytes)")
        summary = _summarize_json(DEST_JSON)
        write_manifest(
            "labor_action_tracker_pages_json",
            {
                "source_id": "labor_action_tracker_pages_json",
                "layer": "E",
                "url": PAGES_JSON_URL,
                "path": str(DEST_JSON.relative_to(ROOT)),
                "bytes": DEST_JSON.stat().st_size,
                "sha256": sha256_file(DEST_JSON),
                "status": "downloaded",
                "notes": (
                    "Cornell–Illinois Labor Action Tracker live Pages JSON "
                    "(StrikeSiteTracker build). Manual LAT methodology; "
                    "strikes ~comprehensive from 2021; protests not complete. "
                    "Map pins = locations, not unique actions."
                ),
                "license_note": "Cite LAT (Cornell ILR & Illinois LER); site terms apply",
                "project_page": PROJECT_PAGE,
                "map_site": MAP_SITE,
                "github_repo": GITHUB_REPO,
                **summary,
            },
        )
        return True, DEST_JSON

    ok, msg = try_download(
        PAGES_JSON_URL,
        DEST_JSON,
        source_id="labor_action_tracker_pages_json",
        notes=(
            "Cornell–Illinois Labor Action Tracker live Pages JSON "
            "(StrikeSiteTracker build). Manual LAT methodology; "
            "strikes ~comprehensive from 2021; protests not complete. "
            "Map pins = locations, not unique actions."
        ),
        license_note="Cite LAT (Cornell ILR & Illinois LER); site terms apply",
        extra={
            "layer": "E",
            "project_page": PROJECT_PAGE,
            "map_site": MAP_SITE,
            "github_repo": GITHUB_REPO,
        },
    )
    print(msg)
    if ok:
        summary = _summarize_json(DEST_JSON)
        # Refresh manifest with row counts.
        write_manifest(
            "labor_action_tracker_pages_json",
            {
                "source_id": "labor_action_tracker_pages_json",
                "layer": "E",
                "url": PAGES_JSON_URL,
                "path": str(DEST_JSON.relative_to(ROOT)),
                "bytes": DEST_JSON.stat().st_size,
                "sha256": sha256_file(DEST_JSON),
                "status": "downloaded",
                "notes": (
                    "Cornell–Illinois Labor Action Tracker live Pages JSON "
                    "(StrikeSiteTracker build). Manual LAT methodology; "
                    "strikes ~comprehensive from 2021; protests not complete. "
                    "Map pins = locations, not unique actions."
                ),
                "license_note": "Cite LAT (Cornell ILR & Illinois LER); site terms apply",
                "project_page": PROJECT_PAGE,
                "map_site": MAP_SITE,
                "github_repo": GITHUB_REPO,
                **summary,
            },
        )
    return ok, DEST_JSON


def fetch_zenodo_xlsx(force: bool = False) -> tuple[bool, Path]:
    if DEST_XLSX.exists() and not force:
        print(f"already present: {DEST_XLSX} ({DEST_XLSX.stat().st_size} bytes)")
        write_manifest(
            "labor_action_tracker_zenodo_xlsx",
            {
                "source_id": "labor_action_tracker_zenodo_xlsx",
                "layer": "E",
                "url": ZENODO_XLSX_URL,
                "doi": ZENODO_DOI,
                "path": str(DEST_XLSX.relative_to(ROOT)),
                "bytes": DEST_XLSX.stat().st_size,
                "sha256": sha256_file(DEST_XLSX),
                "status": "downloaded",
                "notes": (
                    "Zenodo CC-BY-4.0 snapshot file Labor-prod.xlsx "
                    "(third-party packaging of LAT; prefer Pages JSON for live refresh)."
                ),
                "license_note": "CC BY 4.0 (Zenodo record); cite LAT + DOI",
            },
        )
        return True, DEST_XLSX

    ok, msg = try_download(
        ZENODO_XLSX_URL,
        DEST_XLSX,
        source_id="labor_action_tracker_zenodo_xlsx",
        notes=(
            "Zenodo CC-BY-4.0 snapshot file Labor-prod.xlsx "
            "(third-party packaging of LAT; prefer Pages JSON for live refresh)."
        ),
        license_note="CC BY 4.0 (Zenodo record); cite LAT + DOI",
        extra={"layer": "E", "doi": ZENODO_DOI},
    )
    print(msg)
    return ok, DEST_XLSX


def document_email_spreadsheet() -> None:
    write_manifest(
        "labor_action_tracker_email_spreadsheet",
        {
            "source_id": "labor_action_tracker_email_spreadsheet",
            "layer": "E",
            "url": PROJECT_PAGE,
            "status": "documented_only",
            "access": "blocked",
            "blocker": (
                "Official spreadsheet requires emailing Johnnie Kallas "
                "(jkallas@illinois.edu). Not fetched by free automated ingest."
            ),
            "notes": (
                "Prefer public Pages labor_actions.json. Do not invent rows. "
                "Human email request is optional enrichment only."
            ),
            "contact": "jkallas@illinois.edu",
            "local_access_note": str(ACCESS_NOTE.relative_to(ROOT)),
        },
    )


def fetch(force: bool = False, skip_zenodo: bool = False) -> None:
    _write_access_note()
    document_email_spreadsheet()
    ok_json, _ = fetch_pages_json(force=force)
    ok_xlsx = True
    if not skip_zenodo:
        ok_xlsx, _ = fetch_zenodo_xlsx(force=force)
    if not ok_json:
        raise SystemExit(1)
    if not ok_xlsx and not skip_zenodo:
        print("warning: Zenodo XLSX blocked; Pages JSON is primary")


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch Labor Action Tracker free JSON/XLSX")
    p.add_argument("--force", action="store_true")
    p.add_argument("--skip-zenodo", action="store_true")
    args = p.parse_args()
    fetch(force=args.force, skip_zenodo=args.skip_zenodo)


if __name__ == "__main__":
    main()
