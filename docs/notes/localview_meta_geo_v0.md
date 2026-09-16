# LocalView metadata geo note (v0)

Inspected `data/raw/localview/meta_localview.parquet` on 2026-09-16 PT. It has 301,659 rows and 16 columns (35,339,621 bytes; SHA-256 `a7eccd0bdf7e62399207a0caa950a0e4ea33a5677fbcef8bb72f7008b24025f5`). Geo-relevant fields are:

- `st_fips` (`string`, non-null): the codebook's concatenated state + Census FIPS location identifier; it includes 7-digit place-like values, 5-digit county-like values, and semicolon-delimited composites.
- `place_names` (`string`, non-null): Census-style city/town/village/borough and county labels.
- `multiple_cities` (`int64`, only 0/1): whether a video covers multiple cities.
- `predicted_st_fips` (`string`, non-null but often blank; also `UNKNOWN`): an alternate/best-guess identifier for multi-city records.

There is **no dedicated `county_fips` or `county` column**. County FIPS can occur implicitly in `st_fips` for county-labeled records; e.g. the observed composite `st_fips = 41059; 4175650` pairs `Umatilla County; Umatilla city`, while `1703012` is a place-like identifier for `Aurora city`. Thus, do not treat every `st_fips` value as a county or place code based only on length.

## Proposed county crosswalk

1. Preserve the raw `st_fips`, `place_names`, `multiple_cities`, and `predicted_st_fips` values; tokenize semicolon-delimited values without collapsing multi-coverage records.
2. Validate 5-digit county identifiers against an official Census county FIPS table. For 7-digit place identifiers, join state+place FIPS to an official Census place-to-county relationship (Gazetteer/TIGER-derived), retaining one-to-many relationships for places spanning counties.
3. Use county/place labels, `multiple_cities`, and non-empty `predicted_st_fips` to flag ambiguous cases for review; record the crosswalk source/version and confidence. The crosswalk should only add geography mappings to existing LocalView metadata—do not manufacture empirical event rows.

## Crosswalk v0 (implemented 2026-09-16 PT)

**Code:** `src/transform/localview_geo.py` · **Make:** `make crosswalk-localview`

**Inputs (free Census bulk + CT COG table):**

- Counties gazetteer `data/raw/census/2024_Gaz_counties_national.txt` — validate 5-digit county GEOIDs
- Places gazetteer `data/raw/census/2024_Gaz_place_national.txt` — validate 7-digit place GEOIDs
- `data/raw/census/national_places.txt` — place GEOID → county *name(s)* (multi-county as comma lists)
- `data/raw/census/ct_town_to_planning_region.csv` — CT Data Collaborative (MIT) town → 2022 planning-region county-equivalents (needed because 2024 gaz uses COGs, not legacy CT counties)

**Outputs:**

- `data/processed/crosswalks/localview_place_to_county_v0.csv`
- `data/processed/crosswalks/localview_place_to_county_v0_residuals.csv` (confidence `none`/`low`)
- `data/processed/qa/localview_place_to_county_v0_qa.json`

**QA (rebuild 2026-09-16 PT, after CT + name-alias):**

| Metric | Value |
|--------|------:|
| Meta rows | 301,659 |
| Distinct `st_fips` raw | 989 |
| Unique place keys `(st_fips, place_names, multiple_cities, predicted_st_fips)` | 1,150 |
| Keys matched to a single `county_fips` | 1,038 (90.26%) |
| Keys ambiguous / low confidence | 110 (9.57%) |
| Keys unmatched (`none`) | 2 |
| Meta rows with matched county | 269,001 (89.17%) |

**Fallbacks added:** `ct_town_to_planning_region` (3 keys); `place_name_alias_to_county` (2 keys). Residual unmatched: Semmes city (AL `0169240`, 63 rows), Brookhaven city (GA `1310944`, 200 rows).

**Confidence policy:** multi-city / compound `st_fips`, `predicted_st_fips=UNKNOWN`/empty, and multi-county places leave `county_fips` empty (candidates may appear in `all_county_fips`). No FIPS invented.

## Meta spine v0 (implemented 2026-09-16 PT)

**Code:** `src/transform/localview_meta_spine.py` · **Entrypoint:** `python -m src.ingest.localview --include-meta` (also `make fetch-localview-meta` / `make spine-localview`)

**Inputs:**

- `data/raw/localview/meta_localview.parquet`
- `data/processed/crosswalks/localview_place_to_county_v0.csv`

**Join key:** `(st_fips, place_names, multiple_cities, predicted_st_fips)` ↔ crosswalk `(st_fips_raw, …)` (many-to-one).

**Outputs:**

- `data/processed/localview/meta_spine_v0.parquet` — audit fields + `county_fips` / `state` / `county_name` / `all_county_fips` / `confidence` / `method` + `month` (`YYYY-MM`)
- `data/processed/qa/localview_meta_spine_v0_qa.json`

**QA (rebuild 2026-09-16 PT):**

| Metric | Value |
|--------|------:|
| Meta rows | 301,659 |
| Matched county (`county_fips` non-empty) | 269,001 (89.17%) |
| Ambiguous (empty `county_fips`, candidates in `all_county_fips`) | 32,395 |
| Unmatched (no county candidates) | 263 |
| Month parse success (`YYYY-MM`) | 281,074 (93.18%) |
| Month parse fail (null/unparseable `meeting_date`) | 20,585 (6.82%) |
| Spine-ready (`county_fips` ∧ `month`) | 251,070 (83.23%) |
| Rows unjoined to crosswalk | 0 |

**Policy:** no invented FIPS; ambiguous multi-county / compound keys keep empty `county_fips` (candidates in `all_county_fips`). Empty `month` only when `meeting_date` is null/unparseable. CT matched rows use planning-region FIPS (e.g. `09190` Western Connecticut Planning Region).

**Next:** human-review ambiguous/multi-county keys; resolve 2 residual unmatched places if a safe Census GEOID appears; optional `county_fips × month` meeting-count panel once ambiguity policy is set. Still do **not** download transcript tarballs.

