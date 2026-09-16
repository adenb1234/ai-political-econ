"""Layer B — LegiScan free bulk / API.

Bulk portal: https://legiscan.com/datasets  (account required for ZIP pulls)
API docs:    https://api.legiscan.com/      (free key, rate-limited)

This scaffold does NOT invent bill rows. Without LEGISCAN_API_KEY (or a manual
bulk drop under data/raw/legiscan/), fetch is a documented no-op / blocker.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from ._download import ROOT, write_manifest

BULK_PORTAL = "https://legiscan.com/datasets"
API_BASE = "https://api.legiscan.com/"
RAW_DIR = ROOT / "data" / "raw" / "legiscan"


def fetch() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("LEGISCAN_API_KEY", "").strip()
    # Probe portal reachability (often Cloudflare-gated)
    import urllib.error
    import urllib.request

    portal_status = None
    portal_blocker = None
    try:
        req = urllib.request.Request(
            BULK_PORTAL,
            headers={"User-Agent": "ai-backlash-tracker/0.1"},
            method="HEAD",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            portal_status = getattr(resp, "status", None) or resp.getcode()
    except Exception as exc:  # noqa: BLE001
        portal_blocker = str(exc)
        if isinstance(exc, urllib.error.HTTPError):
            portal_status = exc.code

    samples = [x for x in RAW_DIR.glob("*") if x.name != ".gitkeep" and x.is_file()]
    write_manifest(
        "legiscan",
        {
            "source_id": "legiscan",
            "layer": "B",
            "bulk_portal": BULK_PORTAL,
            "api_base": API_BASE,
            "status": "documented_only" if not key and not samples else "partial",
            "api_key_present": bool(key),
            "portal_http_status": portal_status,
            "portal_blocker": portal_blocker,
            "local_files": [str(p.relative_to(ROOT)) for p in samples],
            "notes": (
                "Free tier exists but bulk ZIPs require login; API needs LEGISCAN_API_KEY. "
                "Drop purchased/free bulk extracts into data/raw/legiscan/ when available. "
                "No synthetic bill data is generated here."
            ),
            "license_note": "LegiScan terms of use; attribution required",
        },
    )
    print(f"LegiScan: key={'yes' if key else 'no'}; portal_status={portal_status}; blocker={portal_blocker}")
    print(f"manifest written; raw dir={RAW_DIR}")


def main() -> None:
    argparse.ArgumentParser(description="Document / probe LegiScan free access").parse_args()
    fetch()


if __name__ == "__main__":
    main()
