# Layer C — Moratorium Nation + AI GridWatch geo stub (v0)

**Date:** 2026-09-16 PT  
**Transform:** `src/transform/c_moratoria_geo_stub.py` (`make transform-c-moratoria`)  
**Policy:** best-effort place/county FIPS only; **never invent** `county_fips`. Residuals stay blank.

## Sources (free, CC BY 4.0)

| Source | Raw path | Manifest |
|--------|----------|----------|
| Moratorium Nation inventory | `data/raw/moratorium_nation/moratorium_inventory.csv` | `data/manifests/moratorium_nation_inventory.json` |
| Moratorium Nation state legislation | `data/raw/moratorium_nation/state_legislation.csv` | `data/manifests/moratorium_nation_state_legislation.json` |
| AI GridWatch moratoriums | `data/raw/ai_gridwatch/moratoriums.csv` | `data/manifests/ai_gridwatch_moratoriums.json` |
| AI GridWatch projects (G adjunct) | `data/raw/ai_gridwatch/projects.csv` | `data/manifests/ai_gridwatch_projects.json` |

Fetchers: `src/ingest/moratorium_nation.py`, `src/ingest/ai_gridwatch.py`.

## Crosswalk outputs

- `data/processed/crosswalks/moratorium_nation_place_to_county_v0.csv` (+ `_residuals.csv`)
- `data/processed/crosswalks/ai_gridwatch_place_to_county_v0.csv` (+ `_residuals.csv`)
- QA: `data/processed/qa/c_moratoria_geo_stub_v0_qa.json`

## v0 coverage (this run)

| Source | Rows | Matched FIPS | Match rate | Month parseable |
|--------|------|--------------|------------|-----------------|
| Moratorium Nation | 533 | 372 | 0.6979 | 490 |
| AI GridWatch moratoriums | 853 | 658 | 0.7714 | 808 |

Match kinds use Census county gazetteer + `national_place_by_county2020.txt`. Ambiguous multi-county places are **not** assigned.

## Explicitly not done in v0

- No invented ordinance/event panel counts
- No merge/dedupe across the two trackers (they overlap; collate later)
- Year-only dates do not invent a month
- AI GridWatch `projects.csv` downloaded as G adjunct only — not treated as a national permit registry
