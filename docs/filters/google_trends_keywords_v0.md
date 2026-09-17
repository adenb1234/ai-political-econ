# Google Trends keyword filter — `trends_keywords_v0`

**Version:** `trends_keywords_v0`  
**Access / probe date:** 2026-09-16 (PT)  
**Source:** https://trends.google.com/trends/ (free; **no paid API**)  
**Client:** community `pytrends` with strict sleep/backoff  
**Implemented in:** `src/ingest/google_trends.py`  
**Policy:** ≤5 keywords; state×month grain; **`county_fips` blank**; never invent interest indices.

## Keywords (≤5)

| Keyword | Intent |
|---------|--------|
| `data center` | Local infra / siting salience |
| `ChatGPT` | Consumer generative-AI product salience |
| `artificial intelligence` | Broad AI topic salience |

Kept tiny on purpose: Trends compares relative indices within a pull; more terms multiply rate-limit risk.

## Geography

- **Requested:** US state via pytrends `geo=US-XX` (pilot default: CA, TX, VA, NY, GA).
- **`county_fips`:** always blank in outputs (native Trends is not county).
- **DMA→county:** deferred — needs an explicit crosswalk before any county spine join.

## Time

- Default timeframe: `2023-01-01 2025-12-31`.
- `interest_over_time` often returns **weekly** points; ingest aggregates to **monthly mean** when real data lands.
- Empty / blocked responses → **no rows** (header-only CSV).

## Outputs

- Raw: `data/raw/trends/google_trends_state_month_v0.csv` (+ `ACCESS.md`) — CSV gitignored
- QA: `data/processed/qa/google_trends_state_month_v0_qa.json`
- Manifest: `data/manifests/google_trends.json`

## Explicit non-goals (v0)

- Inventing Trends index numbers when Google returns 429 / CAPTCHA / empty.
- Paid Google Trends / Search API products.
- County FIPS invention or DMA→county crosswalk in this pilot.
- Large keyword lists or aggressive polling.

## Pilot result (2026-09-16 PT)

Full pilot (`--sleep 25`): **540** real rows after one 429+retry; states CA/TX/VA/NY/GA; keywords as above; months 2023-01–2025-12; `county_fips` blank. Manifest status `downloaded`.

## Make target

```bash
make fetch-google-trends
# or: python -m src.ingest.google_trends --probe-only
```
