"""Smoke test — requires Census gazetteer on disk (make fetch-census)."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.geo.fips import load_counties, lookup_fips, normalize_fips


def test_normalize():
    assert normalize_fips("36001") == "36001"
    assert normalize_fips(1001) == "01001"
    assert normalize_fips("na") is None


def test_load_and_lookup():
    counties = load_counties()
    assert len(counties) > 3000
    albany = lookup_fips("36001", counties)
    assert albany is not None
    assert albany.state == "NY"
    assert "Albany" in albany.name


if __name__ == "__main__":
    test_normalize()
    test_load_and_lookup()
    print("ok")
