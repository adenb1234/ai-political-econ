"""Crosswalk residual fallbacks — requires Census + CT town table on disk."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.geo.fips import load_counties
from src.transform.localview_geo import (
    _county_index,
    _national_places_by_name,
    load_ct_town_to_cog,
    load_national_places,
    load_places_gaz,
    map_place_key,
)


def _ctx():
    counties = load_counties()
    by_fips, by_state_name = _county_index(counties)
    national_places = load_national_places()
    return dict(
        by_fips=by_fips,
        by_state_name=by_state_name,
        places_gaz=load_places_gaz(),
        national_places=national_places,
        national_places_by_name=_national_places_by_name(national_places),
        ct_town_to_cog=load_ct_town_to_cog(),
    )


def test_ct_town_to_planning_region():
    ctx = _ctx()
    assert ctx["ct_town_to_cog"], "missing ct_town_to_planning_region.csv"
    row = map_place_key("0918430", "Danbury city", 0, "", 1, **ctx)
    assert row.county_fips == "09190"
    assert row.state == "CT"
    assert row.method == "ct_town_to_planning_region"


def test_ma_name_alias_amherst():
    ctx = _ctx()
    row = map_place_key("2501370", "Amherst town", 0, "", 1, **ctx)
    assert row.county_fips == "25015"
    assert row.state == "MA"
    assert row.method == "place_name_alias_to_county"


def test_semmes_stays_unmatched():
    ctx = _ctx()
    row = map_place_key("0169240", "Semmes city", 0, "", 1, **ctx)
    assert row.county_fips == ""
    assert row.confidence == "none"
    assert row.method == "unmatched_place"


if __name__ == "__main__":
    test_ct_town_to_planning_region()
    test_ma_name_alias_amherst()
    test_semmes_stays_unmatched()
    print("ok")
