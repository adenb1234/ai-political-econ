"""Tiny download helper — no credentials, writes manifests."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = ROOT / "data" / "manifests"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(
    url: str,
    dest: Path,
    *,
    timeout: int = 300,
    user_agent: str = "ai-backlash-tracker/0.1 (free-data scaffold; research)",
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as resp, dest.open("wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    return dest


def write_manifest(name: str, payload: dict[str, Any]) -> Path:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    path = MANIFEST_DIR / f"{name}.json"
    payload = {
        **payload,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def try_download(
    url: str,
    dest: Path,
    *,
    source_id: str,
    notes: str = "",
    license_note: str = "",
    extra: Optional[dict[str, Any]] = None,
) -> tuple[bool, str]:
    """Download and write manifest. Returns (ok, message)."""
    try:
        download(url, dest)
        dig = sha256_file(dest)
        write_manifest(
            source_id,
            {
                "source_id": source_id,
                "url": url,
                "path": str(dest.relative_to(ROOT)),
                "bytes": dest.stat().st_size,
                "sha256": dig,
                "status": "downloaded",
                "notes": notes,
                "license_note": license_note,
                **(extra or {}),
            },
        )
        return True, f"ok {dest} ({dest.stat().st_size} bytes)"
    except Exception as exc:  # noqa: BLE001 — scaffold documents blockers
        write_manifest(
            source_id,
            {
                "source_id": source_id,
                "url": url,
                "path": str(dest.relative_to(ROOT)) if dest else None,
                "status": "blocked",
                "blocker": str(exc),
                "notes": notes,
                "license_note": license_note,
                **(extra or {}),
            },
        )
        return False, f"blocked: {exc}"
