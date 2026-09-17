# Google Trends access (Layer F free pilot)

- Site: https://trends.google.com/trends/
- **No paid API.** Free path only: browser export or community `pytrends`.
- Filter: `trends_keywords_v0` — see `docs/filters/google_trends_keywords_v0.md`
- Keywords (≤5): 'data center', 'ChatGPT', 'artificial intelligence'
- Grain: **state × month** when pulls succeed; **`county_fips` always blank**.
- DMA→county: **deferred** (native Trends geo is often DMA/metro or state).
- Relative index only — series not comparable across pulls without a shared anchor.

## Probe status (2026-09-17T05:02:26.811398+00:00 Z / local PT same calendar day)

- Manifest status: **`downloaded`**
- Trends homepage HTTP: `200`
- Blocker: (none — see detail)

## Detail

- GET https://trends.google.com/trends/ → 200; body_prefix_bytes=256
- call keyword='data center' state=CA failed: TooManyRequestsError: The request failed: Google returned a response with code 429
- Wrote 540 real monthly rows to `data/raw/trends/google_trends_state_month_v0.csv`.

## Policy

- Do **not** invent interest index numbers when Google blocks or returns empty.
- Raw CSV under `data/raw/trends/` is gitignored; commit manifests + QA + this note.
- Re-run `make fetch-google-trends` later with longer `--sleep` if rate-limited.
