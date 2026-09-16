# AI Backlash Tracker

**Owner:** Aden Barton / Economics team  
**Status:** free-data pipeline scaffold (no paid APIs)

## Thesis

Public disapproval of AI is already high and well measured. The constraint is that every number in circulation is a *numerator* — projects blocked, groups formed, bills introduced, protests held — scattered across incompatible sources, with no denominators, no consistent geography, and no fixed release cadence.

This repo collates organized AI opposition evidence in the US into a common schema, keyed to **county FIPS + state** and **month**, published on a fixed cadence, with inputs open. The plumbing is the moat, not the estimator.

**This is not** a sentiment map, a forecast, or a single headline number.

Full product thinking lives in [`docs/WORKING_SPEC.md`](docs/WORKING_SPEC.md).

## Data layers (spine)

| Code | Layer | Free backbone |
|------|-------|---------------|
| A | Deliberation | LocalView (Dataverse) |
| B | Legislation | LegiScan free bulk / Open States |
| C | Ordinances & moratoria | Manual / ordinance text |
| D | News | Media Cloud (free, key); NewsBank = paid, do not depend |
| E | Mobilization | Crowd Counting Consortium (Dataverse) |
| F | Vernacular | Arctic Shift Reddit dumps / Trends |
| G | Project ledger (denominators) | EIA-861, LBNL queues, ISO docks |
| H | Calibration | Pew / Gallup / AP-NORC / ballots |

## Free-source policy

1. **No paid API required for the backbone.** NewsBank is optional enrichment for layer D only.
2. Prefer bulk / dump downloads over rate-limited APIs when both exist.
3. Every shipped series must crosswalk to **county FIPS** (5-digit) and **state**, and aggregate to **month**.
4. Document ToS / license / attribution in `data/manifests/`. Do not invent empirical rows.
5. Pin classifier / prompt versions when LLM enrichment is added later.

## Geography + time keys

- `county_fips`: 5-digit string (state+county), Census GEOID
- `state`: USPS 2-letter
- `month`: `YYYY-MM`

Helpers: [`src/geo/fips.py`](src/geo/fips.py) over Census Gazetteer counties.

## Schema

Two tables; everything else is a view.

- `events` — one row per discrete thing (bill, meeting mention, protest, permit, ordinance)
- `panel` — one row per place × month (counts, denominators, shares)

SQL: [`schema/events.sql`](schema/events.sql), [`schema/panel.sql`](schema/panel.sql)  
Python types: [`src/schema/types.py`](src/schema/types.py)  
Grievance taxonomy: [`docs/TAXONOMY.md`](docs/TAXONOMY.md)

## Repo layout

```
ai-backlash-tracker/
├── README.md
├── docs/           WORKING_SPEC, SOURCES, SOURCE_INVENTORY, TAXONOMY
├── schema/         SQL DDL
├── src/geo/        FIPS helpers
├── src/ingest/     layer fetchers (real free downloads where possible)
├── src/schema/     Python dataclasses / TypedDicts
├── data/raw/       downloaded inputs (gitignored when large)
├── data/manifests/ source metadata JSON
├── data/processed/ derived outputs
├── scripts/        one-shot bootstrap helpers
├── Makefile
└── pyproject.toml / requirements.txt
```

## How to run

```bash
# optional venv
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# (re)fetch free datasets that need no credentials
make fetch-census   # Census county FIPS gazetteer
make fetch-ccc      # Crowd Counting Consortium phase 3 CSV
make fetch-eia      # EIA-861 annual zip
make fetch-all

# sanity-check FIPS table
python -m src.geo.fips --summary
```

Individual ingest modules under `src/ingest/` can also be run as scripts (see each file’s docstring).

## What was downloaded in this scaffold

See [`data/manifests/`](data/manifests/) for SHA256, URL, license notes, and blockers. Real free pulls include Census county FIPS, CCC phase-3 CSV, EIA-861 2024, and LocalView codebook. Large LocalView transcript tarballs and Arctic Shift dumps are documented but not mirrored here.

## License / attribution

Upstream data remain under their original licenses (Census public domain; CCC / LocalView via Harvard Dataverse terms; EIA public domain). Cite sources when publishing derivatives.
