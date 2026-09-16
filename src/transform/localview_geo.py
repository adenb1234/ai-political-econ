"""LocalView meta → county FIPS crosswalk (layer A geo, v0).

Uses:
  - data/raw/localview/meta_localview.parquet
  - Census 2024 counties gazetteer (validate 5-digit county GEOIDs)
  - Census 2024 places gazetteer (validate 7-digit place GEOIDs)
  - Census national_places.txt (place GEOID → county name(s))

Does not invent FIPS for ambiguous multi-city / multi-county / UNKNOWN rows.
Does not download transcript tarballs.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from src.geo.fips import County, load_counties, normalize_fips
from src.ingest._download import ROOT

META_PATH = ROOT / "data" / "raw" / "localview" / "meta_localview.parquet"
PLACES_GAZ = ROOT / "data" / "raw" / "census" / "2024_Gaz_place_national.txt"
NATIONAL_PLACES = ROOT / "data" / "raw" / "census" / "national_places.txt"
# CT Data Collaborative (MIT): town → 2022 planning-region county-equivalents (Census adopted 2022).
CT_TOWN_TO_COG = ROOT / "data" / "raw" / "census" / "ct_town_to_planning_region.csv"
OUT_CSV = ROOT / "data" / "processed" / "crosswalks" / "localview_place_to_county_v0.csv"
OUT_QA = ROOT / "data" / "processed" / "qa" / "localview_place_to_county_v0_qa.json"
OUT_RESIDUALS = (
    ROOT / "data" / "processed" / "crosswalks" / "localview_place_to_county_v0_residuals.csv"
)

COUNTY_LABEL_RE = re.compile(
    r"(?i)\b(county|parish|census area|borough|municipio|city and borough|municipality)\b"
)
# Independent cities / county-equivalents often labeled "X city"
INDEPENDENT_CITY_RE = re.compile(r"(?i)\bcity\b")


@dataclass(frozen=True)
class PlaceRef:
    geoid: str
    state: str
    name: str
    county_names: tuple[str, ...]


def _split_tokens(raw: str) -> list[str]:
    s = (raw or "").strip()
    if not s:
        return []
    # LocalView compounds use "; " separators (sometimes without space).
    parts = re.split(r"[;|]", s)
    return [p.strip() for p in parts if p.strip()]


def _is_county_label(place_names: str) -> bool:
    return bool(COUNTY_LABEL_RE.search(place_names or ""))


def _norm_name(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    for suf in (
        " county",
        " parish",
        " census area",
        " city and borough",
        " borough",
        " municipality",
        " municipio",
        " city",
        " town",
        " village",
        " cdp",
    ):
        if s.endswith(suf):
            s = s[: -len(suf)]
            break
    return s


def load_places_gaz(path: Path | None = None) -> dict[str, str]:
    """geoid → USPS state."""
    path = path or PLACES_GAZ
    if not path.exists():
        raise FileNotFoundError(f"Places gazetteer missing: {path}. Run: make fetch-census-places")
    out: dict[str, str] = {}
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            cleaned = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}
            geoid = (cleaned.get("GEOID") or "").strip()
            usps = (cleaned.get("USPS") or "").strip().upper()
            if geoid and usps:
                out[geoid] = usps
    return out


def load_national_places(path: Path | None = None) -> dict[str, PlaceRef]:
    """geoid → PlaceRef with county name list (deduped, order preserved)."""
    path = path or NATIONAL_PLACES
    if not path.exists():
        raise FileNotFoundError(f"national_places.txt missing: {path}. Run: make fetch-census-places")
    text = path.read_bytes().decode("latin-1")
    lines = [ln.strip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if ln.strip()]
    if not lines:
        return {}
    # Aggregate duplicate geoids / multi-county name strings.
    buckets: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for ln in lines[1:]:
        parts = ln.split("|")
        if len(parts) < 7:
            continue
        state, statefp, placefp, placename, _typ, _func, county = parts[:7]
        geoid = f"{statefp.strip()}{placefp.strip()}"
        buckets[geoid].append((state.strip().upper(), placename.strip(), county.strip()))

    out: dict[str, PlaceRef] = {}
    for geoid, rows in buckets.items():
        state = rows[0][0]
        name = rows[0][1]
        county_names: list[str] = []
        seen: set[str] = set()
        for _st, _nm, county in rows:
            # Split "A County, B County"
            for chunk in re.split(r"\s*,\s*", county):
                chunk = chunk.strip()
                if not chunk:
                    continue
                key = chunk.lower()
                if key not in seen:
                    seen.add(key)
                    county_names.append(chunk)
        out[geoid] = PlaceRef(geoid=geoid, state=state, name=name, county_names=tuple(county_names))
    return out



def load_ct_town_to_cog(path: Path | None = None) -> dict[str, tuple[str, str]]:
    """Normalize town name → (5-digit planning-region FIPS, region name).

    Source: CT Data Collaborative ct-town-to-planning-region (MIT), derived from
    Census TIGER 2022 county subdivisions after CT county→COG change.
    Optional file — empty dict if missing.
    """
    path = path or CT_TOWN_TO_COG
    if not path.exists():
        return {}
    out: dict[str, tuple[str, str]] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            town = (row.get("town_name") or "").strip()
            ce_raw = (row.get("ce_fips_2022") or "").strip()
            ce_name = (row.get("ce_name_2022") or "").strip()
            if not town or not ce_raw:
                continue
            try:
                fips = f"{int(ce_raw):05d}"
            except ValueError:
                continue
            out[_norm_name(town)] = (fips, ce_name)
    return out


def _national_places_by_name(
    national_places: dict[str, PlaceRef],
) -> dict[tuple[str, str], list[PlaceRef]]:
    by_name: dict[tuple[str, str], list[PlaceRef]] = defaultdict(list)
    for ref in national_places.values():
        by_name[(ref.state, _norm_name(ref.name))].append(ref)
    return by_name


def _name_alias_candidates(place_names: str) -> list[str]:
    """Normalized name variants for MA city/town dual-status and similar labels."""
    base = _norm_name(place_names)
    if not base:
        return []
    out: list[str] = [base]
    if base.endswith(" town"):
        out.append(base[: -len(" town")])
    else:
        out.append(f"{base} town")
    # Dedup preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for n in out:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq


def _try_ct_town_cog(
    place_names: str,
    *,
    by_fips: dict[str, County],
    ct_town_to_cog: dict[str, tuple[str, str]],
    tok: str,
    method_prefix: str,
) -> CrosswalkRow | None:
    """Map CT place label → planning-region county-equivalent when gazetteer has COGs only."""
    if not ct_town_to_cog:
        return None
    for cand in _name_alias_candidates(place_names):
        hit = ct_town_to_cog.get(cand)
        if not hit:
            continue
        fips, ce_name = hit
        c = by_fips.get(fips)
        if not c:
            continue
        pref = f"{method_prefix}" if method_prefix else ""
        return CrosswalkRow(
            st_fips_raw=tok,
            place_names=place_names,
            multiple_cities=0,
            predicted_st_fips="",
            n_meta_rows=0,
            county_fips=c.fips,
            state=c.state,
            county_name=c.name,
            all_county_fips=c.fips,
            confidence="medium",
            method=f"{pref}ct_town_to_planning_region",
            notes=(
                f"CT legacy county names obsolete in 2024 gaz; "
                f"mapped via town→{ce_name} (CT Data Collaborative / Census COG)"
            ),
        )
    return None


def _try_name_alias_place(
    state: str,
    place_names: str,
    *,
    by_state_name: dict[tuple[str, str], County],
    by_name: dict[tuple[str, str], list[PlaceRef]],
    tok: str,
    in_gaz: bool,
    method_prefix: str,
) -> CrosswalkRow | None:
    """When GEOID missing from national_places, try unique same-state name alias."""
    if not state:
        return None
    refs: list[PlaceRef] = []
    seen_geoids: set[str] = set()
    for cand in _name_alias_candidates(place_names):
        for ref in by_name.get((state.upper(), cand), []):
            if ref.geoid not in seen_geoids:
                seen_geoids.add(ref.geoid)
                refs.append(ref)
    if not refs:
        return None
    # Union counties across alias hits; accept only if single county.
    counties: list[County] = []
    seen_fips: set[str] = set()
    for ref in refs:
        for c in _resolve_county_names(ref.state, ref.county_names, by_state_name):
            if c.fips not in seen_fips:
                seen_fips.add(c.fips)
                counties.append(c)
    pref = f"{method_prefix}" if method_prefix else ""
    if len(counties) == 1:
        c = counties[0]
        return CrosswalkRow(
            st_fips_raw=tok,
            place_names=place_names,
            multiple_cities=0,
            predicted_st_fips="",
            n_meta_rows=0,
            county_fips=c.fips,
            state=c.state,
            county_name=c.name,
            all_county_fips=c.fips,
            confidence="medium",
            method=f"{pref}place_name_alias_to_county",
            notes=(
                "GEOID absent/stale in national_places; unique same-state name alias "
                f"→ {refs[0].geoid} {refs[0].name}"
                + ("" if in_gaz else "; place GEOID not in 2024 places gaz")
            ),
        )
    if len(counties) > 1:
        return CrosswalkRow(
            st_fips_raw=tok,
            place_names=place_names,
            multiple_cities=0,
            predicted_st_fips="",
            n_meta_rows=0,
            county_fips="",
            state=state.upper(),
            county_name="",
            all_county_fips=";".join(c.fips for c in counties),
            confidence="low",
            method=f"{pref}ambiguous_name_alias",
            notes="name alias spans multiple counties; FIPS not invented",
        )
    return None


def _county_index(counties: Iterable[County]) -> tuple[dict[str, County], dict[tuple[str, str], County]]:
    by_fips = {c.fips: c for c in counties}
    by_state_name: dict[tuple[str, str], County] = {}
    for c in counties:
        by_state_name[(c.state, _norm_name(c.name))] = c
        # Also index full lower name
        by_state_name[(c.state, c.name.strip().lower())] = c
    return by_fips, by_state_name


def _resolve_county_names(
    state: str,
    county_names: Iterable[str],
    by_state_name: dict[tuple[str, str], County],
) -> list[County]:
    found: list[County] = []
    seen: set[str] = set()
    st = state.upper()
    for raw in county_names:
        c = by_state_name.get((st, _norm_name(raw))) or by_state_name.get((st, raw.strip().lower()))
        if c and c.fips not in seen:
            seen.add(c.fips)
            found.append(c)
    return found


@dataclass
class CrosswalkRow:
    st_fips_raw: str
    place_names: str
    multiple_cities: int
    predicted_st_fips: str
    n_meta_rows: int
    county_fips: str
    state: str
    county_name: str
    all_county_fips: str
    confidence: str
    method: str
    notes: str


def _map_single_token(
    token: str,
    place_names: str,
    *,
    by_fips: dict[str, County],
    by_state_name: dict[tuple[str, str], County],
    places_gaz: dict[str, str],
    national_places: dict[str, PlaceRef],
    national_places_by_name: dict[tuple[str, str], list[PlaceRef]] | None = None,
    ct_town_to_cog: dict[str, tuple[str, str]] | None = None,
    method_prefix: str = "",
) -> CrosswalkRow | None:
    """Map one GEOID-like token. Returns None if token empty."""
    tok = token.strip()
    if not tok:
        return None
    pref = f"{method_prefix}" if method_prefix else ""

    # Non-digit / UNKNOWN
    if tok.upper() == "UNKNOWN" or not tok.replace(" ", "").isdigit():
        return CrosswalkRow(
            st_fips_raw=tok,
            place_names=place_names,
            multiple_cities=0,
            predicted_st_fips="",
            n_meta_rows=0,
            county_fips="",
            state="",
            county_name="",
            all_county_fips="",
            confidence="none",
            method=f"{pref}unmatched_nondigit".lstrip("_"),
            notes="non-digit or UNKNOWN token",
        )

    digits = re.sub(r"\D", "", tok)

    # 5-digit (or shorter zero-padded) county GEOID
    if len(digits) <= 5:
        fips = normalize_fips(digits)
        if fips and fips in by_fips:
            c = by_fips[fips]
            conf = "high" if _is_county_label(place_names) else "medium"
            method = f"{pref}county_geoid_validated"
            return CrosswalkRow(
                st_fips_raw=tok,
                place_names=place_names,
                multiple_cities=0,
                predicted_st_fips="",
                n_meta_rows=0,
                county_fips=c.fips,
                state=c.state,
                county_name=c.name,
                all_county_fips=c.fips,
                confidence=conf,
                method=method,
                notes="validated against 2024 counties gazetteer",
            )
        return CrosswalkRow(
            st_fips_raw=tok,
            place_names=place_names,
            multiple_cities=0,
            predicted_st_fips="",
            n_meta_rows=0,
            county_fips="",
            state="",
            county_name="",
            all_county_fips="",
            confidence="none",
            method=f"{pref}unmatched_county_geoid",
            notes="5-digit token not in counties gazetteer",
        )

    # 7-digit place GEOID
    if len(digits) == 7:
        in_gaz = digits in places_gaz
        pref_ref = national_places.get(digits)
        state = (pref_ref.state if pref_ref else places_gaz.get(digits, "")) or ""

        # County-labeled 7-digit: sometimes county FIPS encoded as placefp (e.g. Spartanburg).
        if _is_county_label(place_names):
            as_county = normalize_fips(digits[2:])
            if as_county and as_county in by_fips:
                c = by_fips[as_county]
                return CrosswalkRow(
                    st_fips_raw=tok,
                    place_names=place_names,
                    multiple_cities=0,
                    predicted_st_fips="",
                    n_meta_rows=0,
                    county_fips=c.fips,
                    state=c.state,
                    county_name=c.name,
                    all_county_fips=c.fips,
                    confidence="medium",
                    method=f"{pref}county_label_placefp_as_county",
                    notes="county-labeled row; placefp validated as county GEOID",
                )

        if pref_ref:
            counties = _resolve_county_names(pref_ref.state, pref_ref.county_names, by_state_name)
            if len(counties) == 1:
                c = counties[0]
                conf = "high" if in_gaz else "medium"
                return CrosswalkRow(
                    st_fips_raw=tok,
                    place_names=place_names,
                    multiple_cities=0,
                    predicted_st_fips="",
                    n_meta_rows=0,
                    county_fips=c.fips,
                    state=c.state,
                    county_name=c.name,
                    all_county_fips=c.fips,
                    confidence=conf,
                    method=f"{pref}place_to_county",
                    notes="national_places → counties gazetteer"
                    + ("" if in_gaz else "; place GEOID not in 2024 places gaz"),
                )
            if len(counties) > 1:
                all_f = ";".join(c.fips for c in counties)
                return CrosswalkRow(
                    st_fips_raw=tok,
                    place_names=place_names,
                    multiple_cities=0,
                    predicted_st_fips="",
                    n_meta_rows=0,
                    county_fips="",
                    state=pref_ref.state,
                    county_name="",
                    all_county_fips=all_f,
                    confidence="low",
                    method=f"{pref}ambiguous_multi_county_place",
                    notes=f"place spans {len(counties)} counties; FIPS not invented",
                )
            # CT: 2024 gazetteer uses planning regions; national_places still has legacy counties.
            if pref_ref.state == "CT":
                ct_hit = _try_ct_town_cog(
                    place_names,
                    by_fips=by_fips,
                    ct_town_to_cog=ct_town_to_cog or {},
                    tok=tok,
                    method_prefix=method_prefix,
                )
                if ct_hit is not None:
                    return ct_hit
            return CrosswalkRow(
                st_fips_raw=tok,
                place_names=place_names,
                multiple_cities=0,
                predicted_st_fips="",
                n_meta_rows=0,
                county_fips="",
                state=pref_ref.state,
                county_name="",
                all_county_fips="",
                confidence="none",
                method=f"{pref}unmatched_county_name",
                notes=f"county names not resolved: {list(pref_ref.county_names)}",
            )

        # VA / independent-city pattern: place missing, but placefp is county-equivalent
        # whose name matches the LocalView label.
        as_county = normalize_fips(digits[2:])
        if as_county and as_county in by_fips:
            c = by_fips[as_county]
            if _norm_name(c.name) == _norm_name(place_names) or (
                INDEPENDENT_CITY_RE.search(place_names or "")
                and _norm_name(c.name) == _norm_name(place_names)
            ):
                return CrosswalkRow(
                    st_fips_raw=tok,
                    place_names=place_names,
                    multiple_cities=0,
                    predicted_st_fips="",
                    n_meta_rows=0,
                    county_fips=c.fips,
                    state=c.state,
                    county_name=c.name,
                    all_county_fips=c.fips,
                    confidence="medium",
                    method=f"{pref}county_equiv_geoid",
                    notes="independent-city / county-equivalent GEOID match by name",
                )

        # Name-alias fallback (e.g. MA Amherst Town city ↔ Amherst town GEOID).
        alias_hit = _try_name_alias_place(
            state,
            place_names,
            by_state_name=by_state_name,
            by_name=national_places_by_name or {},
            tok=tok,
            in_gaz=in_gaz,
            method_prefix=method_prefix,
        )
        if alias_hit is not None:
            return alias_hit

        # CT town → planning region when GEOID path failed entirely.
        if (state == "CT" or digits.startswith("09")):
            ct_hit = _try_ct_town_cog(
                place_names,
                by_fips=by_fips,
                ct_town_to_cog=ct_town_to_cog or {},
                tok=tok,
                method_prefix=method_prefix,
            )
            if ct_hit is not None:
                return ct_hit

        return CrosswalkRow(
            st_fips_raw=tok,
            place_names=place_names,
            multiple_cities=0,
            predicted_st_fips="",
            n_meta_rows=0,
            county_fips="",
            state=state,
            county_name="",
            all_county_fips="",
            confidence="none",
            method=f"{pref}unmatched_place",
            notes="7-digit not in national_places / no safe county equiv",
        )

    return CrosswalkRow(
        st_fips_raw=tok,
        place_names=place_names,
        multiple_cities=0,
        predicted_st_fips="",
        n_meta_rows=0,
        county_fips="",
        state="",
        county_name="",
        all_county_fips="",
        confidence="none",
        method=f"{pref}unmatched_length",
        notes=f"unexpected digit length {len(digits)}",
    )


def map_place_key(
    st_fips: str,
    place_names: str,
    multiple_cities: int,
    predicted_st_fips: str,
    n_meta_rows: int,
    *,
    by_fips: dict[str, County],
    by_state_name: dict[tuple[str, str], County],
    places_gaz: dict[str, str],
    national_places: dict[str, PlaceRef],
    national_places_by_name: dict[tuple[str, str], list[PlaceRef]] | None = None,
    ct_town_to_cog: dict[str, tuple[str, str]] | None = None,
) -> CrosswalkRow:
    tokens = _split_tokens(st_fips)
    pred = (predicted_st_fips or "").strip()

    # Compound / multi-token st_fips
    if len(tokens) > 1 or int(multiple_cities or 0) == 1:
        # Try predicted first when usable
        if pred and pred.upper() != "UNKNOWN":
            pred_tokens = _split_tokens(pred)
            if len(pred_tokens) == 1:
                mapped = _map_single_token(
                    pred_tokens[0],
                    place_names,
                    by_fips=by_fips,
                    by_state_name=by_state_name,
                    places_gaz=places_gaz,
                    national_places=national_places,
                    national_places_by_name=national_places_by_name,
                    ct_town_to_cog=ct_town_to_cog,
                    method_prefix="predicted_",
                )
                if mapped and mapped.county_fips:
                    mapped.st_fips_raw = st_fips
                    mapped.place_names = place_names
                    mapped.multiple_cities = int(multiple_cities or 0)
                    mapped.predicted_st_fips = pred
                    mapped.n_meta_rows = n_meta_rows
                    if mapped.confidence == "high":
                        mapped.confidence = "medium"
                    mapped.notes = (mapped.notes + "; from predicted_st_fips for multi-city").strip("; ")
                    return mapped

        # If every token resolves to the *same* single county, accept as medium.
        resolved: list[CrosswalkRow] = []
        for t in tokens:
            m = _map_single_token(
                t,
                place_names,
                by_fips=by_fips,
                by_state_name=by_state_name,
                places_gaz=places_gaz,
                national_places=national_places,
                national_places_by_name=national_places_by_name,
                ct_town_to_cog=ct_town_to_cog,
            )
            if m:
                resolved.append(m)
        fips_set = {m.county_fips for m in resolved if m.county_fips}
        if len(fips_set) == 1:
            base = next(m for m in resolved if m.county_fips)
            base.st_fips_raw = st_fips
            base.place_names = place_names
            base.multiple_cities = int(multiple_cities or 0)
            base.predicted_st_fips = pred
            base.n_meta_rows = n_meta_rows
            base.confidence = "medium"
            base.method = "compound_tokens_agree"
            base.notes = "all resolvable tokens agree on one county"
            return base

        all_f = sorted({m.county_fips for m in resolved if m.county_fips})
        return CrosswalkRow(
            st_fips_raw=st_fips,
            place_names=place_names,
            multiple_cities=int(multiple_cities or 0),
            predicted_st_fips=pred,
            n_meta_rows=n_meta_rows,
            county_fips="",
            state="",
            county_name="",
            all_county_fips=";".join(all_f),
            confidence="low" if all_f else "none",
            method="ambiguous_compound",
            notes="multi-city/compound st_fips; no single county invented"
            + ("; predicted UNKNOWN/empty" if not pred or pred.upper() == "UNKNOWN" else ""),
        )

    # Single token
    if not tokens:
        return CrosswalkRow(
            st_fips_raw=st_fips,
            place_names=place_names,
            multiple_cities=int(multiple_cities or 0),
            predicted_st_fips=pred,
            n_meta_rows=n_meta_rows,
            county_fips="",
            state="",
            county_name="",
            all_county_fips="",
            confidence="none",
            method="empty_st_fips",
            notes="empty st_fips",
        )

    mapped = _map_single_token(
        tokens[0],
        place_names,
        by_fips=by_fips,
        by_state_name=by_state_name,
        places_gaz=places_gaz,
        national_places=national_places,
        national_places_by_name=national_places_by_name,
        ct_town_to_cog=ct_town_to_cog,
    )
    assert mapped is not None
    mapped.st_fips_raw = st_fips
    mapped.place_names = place_names
    mapped.multiple_cities = int(multiple_cities or 0)
    mapped.predicted_st_fips = pred
    mapped.n_meta_rows = n_meta_rows
    return mapped


def build_crosswalk(
    meta_path: Path | None = None,
) -> tuple[list[CrosswalkRow], dict]:
    meta_path = meta_path or META_PATH
    if not meta_path.exists():
        raise FileNotFoundError(f"LocalView meta missing: {meta_path}")

    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("pyarrow required. Install: .venv/bin/pip install pyarrow") from exc

    table = pq.read_table(
        meta_path,
        columns=["st_fips", "place_names", "multiple_cities", "predicted_st_fips"],
    )
    df = table.to_pandas()
    # Unique place keys
    grouped = (
        df.groupby(["st_fips", "place_names", "multiple_cities", "predicted_st_fips"], dropna=False)
        .size()
        .reset_index(name="n_meta_rows")
    )

    counties = load_counties()
    by_fips, by_state_name = _county_index(counties)
    places_gaz = load_places_gaz()
    national_places = load_national_places()
    national_places_by_name = _national_places_by_name(national_places)
    ct_town_to_cog = load_ct_town_to_cog()

    rows: list[CrosswalkRow] = []
    for rec in grouped.itertuples(index=False):
        rows.append(
            map_place_key(
                str(rec.st_fips),
                str(rec.place_names),
                int(rec.multiple_cities or 0),
                str(rec.predicted_st_fips or ""),
                int(rec.n_meta_rows),
                by_fips=by_fips,
                by_state_name=by_state_name,
                places_gaz=places_gaz,
                national_places=national_places,
                national_places_by_name=national_places_by_name,
                ct_town_to_cog=ct_town_to_cog,
            )
        )

    # Also emit unique by st_fips|place_names collapsing predicted variants? Keep full key grain.
    n_keys = len(rows)
    matched = sum(1 for r in rows if r.county_fips)
    ambiguous = sum(1 for r in rows if r.method.startswith("ambiguous") or r.confidence == "low")
    distinct_st = len({r.st_fips_raw for r in rows})
    method_counts = Counter(r.method for r in rows)
    conf_counts = Counter(r.confidence for r in rows)

    # Meeting-row weighted rates
    meta_total = int(df.shape[0])
    meta_matched = int(sum(r.n_meta_rows for r in rows if r.county_fips))

    qa = {
        "crosswalk_version": "localview_place_to_county_v0",
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "meta_path": str(meta_path.relative_to(ROOT)),
        "meta_rows": meta_total,
        "distinct_st_fips_raw": distinct_st,
        "unique_place_keys": n_keys,
        "keys_matched_to_county": matched,
        "keys_matched_share": round(matched / n_keys, 4) if n_keys else 0.0,
        "keys_ambiguous_or_low": ambiguous,
        "keys_ambiguous_share": round(ambiguous / n_keys, 4) if n_keys else 0.0,
        "meta_rows_matched_to_county": meta_matched,
        "meta_rows_matched_share": round(meta_matched / meta_total, 4) if meta_total else 0.0,
        "confidence_counts": dict(conf_counts),
        "method_counts": dict(method_counts),
        "sources": {
            "counties_gaz": "data/raw/census/2024_Gaz_counties_national.txt",
            "places_gaz": "data/raw/census/2024_Gaz_place_national.txt",
            "national_places": "data/raw/census/national_places.txt",
            "ct_town_to_planning_region": (
                "data/raw/census/ct_town_to_planning_region.csv"
                if ct_town_to_cog
                else None
            ),
        },
        "residual_unmatched_keys": sum(1 for r in rows if r.confidence == "none"),
        "residual_unmatched_meta_rows": int(
            sum(r.n_meta_rows for r in rows if r.confidence == "none")
        ),
        "notes": (
            "Unique keys are (st_fips, place_names, multiple_cities, predicted_st_fips). "
            "Multi-county places and unresolved multi-city compounds leave county_fips empty "
            "and list candidates in all_county_fips when known. "
            "CT rows may use town→planning-region COG FIPS (2022 Census change). "
            "No empirical event rows invented."
        ),
    }
    return rows, qa


def write_outputs(
    rows: list[CrosswalkRow],
    qa: dict,
    out_csv: Path | None = None,
    out_qa: Path | None = None,
    out_residuals: Path | None = None,
) -> tuple[Path, Path, Path]:
    out_csv = out_csv or OUT_CSV
    out_qa = out_qa or OUT_QA
    out_residuals = out_residuals or OUT_RESIDUALS
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_qa.parent.mkdir(parents=True, exist_ok=True)
    out_residuals.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "st_fips_raw",
        "place_names",
        "multiple_cities",
        "predicted_st_fips",
        "n_meta_rows",
        "county_fips",
        "state",
        "county_name",
        "all_county_fips",
        "confidence",
        "method",
        "notes",
    ]
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: getattr(r, k) for k in fieldnames})

    residual_rows = [r for r in rows if r.confidence in {"none", "low"}]
    with out_residuals.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in residual_rows:
            w.writerow({k: getattr(r, k) for k in fieldnames})

    qa = dict(qa)
    qa["residuals_path"] = str(out_residuals.relative_to(ROOT))
    qa["residuals_keys"] = len(residual_rows)
    out_qa.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    return out_csv, out_qa, out_residuals


def main() -> None:
    p = argparse.ArgumentParser(description="Build LocalView place→county FIPS crosswalk v0")
    p.add_argument("--meta", type=str, default=None)
    args = p.parse_args()
    meta = Path(args.meta) if args.meta else None
    rows, qa = build_crosswalk(meta)
    csv_path, qa_path, res_path = write_outputs(rows, qa)
    print(f"wrote {csv_path} ({len(rows)} keys)")
    print(f"wrote {qa_path}")
    print(f"wrote {res_path} (none+low residuals)")
    print(
        "QA:",
        f"keys={qa['unique_place_keys']}",
        f"matched={qa['keys_matched_to_county']} ({qa['keys_matched_share']})",
        f"ambiguous_or_low={qa['keys_ambiguous_or_low']}",
        f"meta_matched_share={qa['meta_rows_matched_share']}",
    )


if __name__ == "__main__":
    main()
