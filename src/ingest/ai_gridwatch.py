"""Layer C (+ G adjunct) — AI GridWatch open-data CSVs (CC BY 4.0)."""

from __future__ import annotations

import argparse
from pathlib import Path

from ._download import ROOT, try_download

PORTAL = "https://aigridwatch.com/open-data"
BASE = "https://aigridwatch.com/data"

FILES = [
    (
        f"{BASE}/moratoriums.csv",
        ROOT / "data" / "raw" / "ai_gridwatch" / "moratoriums.csv",
        "ai_gridwatch_moratoriums",
        "AI GridWatch U.S. data center moratorium & community action tracker. Layer C.",
        "C",
    ),
    (
        f"{BASE}/projects.csv",
        ROOT / "data" / "raw" / "ai_gridwatch" / "projects.csv",
        "ai_gridwatch_projects",
        "AI GridWatch project intelligence tracker (proposals/stages). Layer G adjunct; "
        "curated rows only — not a national permit registry; do not invent outcomes.",
        "G",
    ),
]


def fetch(force: bool = False) -> list[Path]:
    out: list[Path] = []
    for url, dest, sid, notes, layer in FILES:
        if dest.exists() and not force:
            print(f"already present: {dest} ({dest.stat().st_size} bytes)")
            out.append(dest)
            continue
        ok, msg = try_download(
            url,
            dest,
            source_id=sid,
            notes=notes,
            license_note="CC BY 4.0 (AI GridWatch)",
            extra={
                "layer": layer,
                "portal": PORTAL,
                "access_date_pt": "2026-09-16",
            },
        )
        print(msg)
        if not ok:
            raise SystemExit(1)
        out.append(dest)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch AI GridWatch open-data CSVs")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    fetch(force=args.force)


if __name__ == "__main__":
    main()
