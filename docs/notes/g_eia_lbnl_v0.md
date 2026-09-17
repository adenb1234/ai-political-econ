# Layer G — EIA-861 + LBNL Queued Up transforms (v0)

Access date: **2026-09-16 PT**. Schema freeze: do **not** edit `schema/events.sql`, `schema/panel.sql`, or taxonomy v0.1 from this work.

## Honest labels

| Source | What the v0 metric is | What it is **not** |
|--------|----------------------|--------------------|
| LBNL Queued Up 2026 | Generation/storage **interconnection queue activity** by county_fips×month (and state×month) | Data-center permit proposed/approved/denied/delayed counts |
| EIA Form 861 2024 | Utility **service-territory** coverage (utility→county best-effort FIPS) + utility→state annual stub | Monthly panel grain; DC siting permits |

WORKING_SPEC failure mode G still holds: **no national data-center permit registry**.

## LBNL (`make transform-lbnl`)

- **Code:** `src/transform/lbnl_queue_to_panel.py`
- **Input:** `data/raw/lbnl/LBNL_Ix_Queue_Data_File_thru2025.xlsx` sheet `03. Complete Queue Data`
- **Month:** primary `q_date`; fallbacks `ia_date`, `on_date`, `wd_date`, `prop_date`
- **Geo:** upstream `fips_code` via `normalize_fips`; state-only / no-geo logged in QA; never invent FIPS
- **QA (2026-09-16 PT):** 38,201 queue rows; county FIPS 36,325 (**0.9509**); month parseable 38,084 (**0.9969**); county×month panel 23,699; state×month 7,311
- **Outputs:** `data/processed/panel/lbnl_ix_queue_activity_v0.csv` (+ state_month + sample); `data/processed/qa/lbnl_ix_queue_activity_v0_qa.json`

## EIA-861 (`make transform-eia`)

- **Code:** `src/transform/eia_861_to_coverage.py`
- **Inputs:** `data/raw/eia/Service_Territory_2024.xlsx` (`Counties_States`), `Utility_Data_2024.xlsx` (`States`); zip `f8612024.zip` already on disk
- **Geo:** EIA county *name* + state → Census 2024 counties gazetteer (suffix strip, St/Saint, hyphen/space, limited unique aliases). Ambiguous VA/MD/MO county-vs-city names and CT legacy counties get **no** FIPS
- **QA (2026-09-16 PT):** 11,776 territory rows; matched FIPS 11,730 (**0.9961**); ambiguous 11; unmatched 35; utility/state rows 1,701
- **Outputs:** `data/processed/crosswalks/eia_861_utility_county_v0.csv`; `data/processed/panel/eia_861_utility_state_v0.csv` (+ sample); `data/processed/qa/eia_861_coverage_v0_qa.json`

### Documented EIA gaps

1. **CT legacy counties** — EIA still uses Fairfield/Hartford/…; Census 2024 gaz uses COGs.
2. **County vs independent city** — e.g. Fairfax, Baltimore, St Louis left `ambiguous`.
3. **AK historical census areas** — pre-split labels (Valdez Cordova, etc.) unmatched.
4. **Annual grain only** — do not treat as county×month without an explicit policy.

## Make

```bash
make transform-g          # lbnl + eia
make transform-lbnl
make transform-eia
```
