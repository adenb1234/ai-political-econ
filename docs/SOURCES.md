# Sources — free-data access notes

Policy: backbone uses **no paid APIs**. Keys are optional enrichment only.  
Per-layer free status, verified raw state, blockers, and next steps (A/B/E/F/G) are tracked in [`SOURCE_INVENTORY.md`](SOURCE_INVENTORY.md). This file remains the access-URL reference.
Refresh cadence targets match [`WORKING_SPEC.md`](WORKING_SPEC.md).

**Inventory pointer:** the matrix is checked against `data/raw/` and `data/manifests/` as of 2026-09-16 PT; this document keeps the source URLs and access notes.

---
## E — Crowd Counting Consortium (mobilization)

| | |
|---|---|
| **What** | US protest / rally / demonstration event rows since 2017 |
| **Access** | Free public Harvard Dataverse (no key) |
| **Phase 3 (2025–)** | DOI [`10.7910/DVN/RI9JFU`](https://doi.org/10.7910/DVN/RI9JFU) — file `ccc-phase3-public.csv` |
| **Direct download** | `https://dataverse.harvard.edu/api/access/datafile/14226873` |
| **Phase 2 (2021–2024)** | DOI [`10.7910/DVN/9MMYDI`](https://doi.org/10.7910/DVN/9MMYDI) |
| **Project page** | https://ash.harvard.edu/programs/crowd-counting-consortium/ |
| **Dataverse root** | https://dataverse.harvard.edu/dataverse/crowdcountingconsortium |
| **Geo** | `fips_code` (5-digit) already present on many rows; also locality/state |
| **Fetcher** | `src/ingest/ccc.py` |
| **Sample on disk** | `data/raw/ccc/ccc-phase3-public.csv` (~65k rows, ~46 MB) |

Filter downstream for AI / data-center / energy-related claims via `claims_*` / `issue_tags_*` / `organizations` — do not invent filters here.

**Transform (2026-09-16 PT):** `make transform-ccc` → `src/transform/ccc_to_events.py`; keyword rules `docs/filters/ccc_ai_keywords_v0.md` (`ccc_rules_v0`).

---

## B — Legislation (LegiScan / Open States)

### LegiScan free bulk

| | |
|---|---|
| **What** | All 50 states + Congress: bills, sponsors, roll calls, full text |
| **Access** | Free tier / bulk datasets — **account required** for bulk ZIP pulls |
| **Portal** | https://legiscan.com/datasets |
| **API** | https://api.legiscan.com/ (free key, rate-limited) |
| **Blocker for this scaffold** | Bulk download redirects / Cloudflare (HTTP 403 from this box without login). No key configured. |
| **Fetcher** | `src/ingest/legiscan.py` (documents URLs; skips download without `LEGISCAN_API_KEY`) |

### Open States

| | |
|---|---|
| **What** | Committee / bill detail (v3 API); useful complement to LegiScan |
| **Docs** | https://docs.openstates.org/ |
| **Access** | API key required for production use (GraphQL / REST) |
| **Public sample** | Schema + docs are public; no credential-free bulk bill dump mirrored here |
| **Fetcher** | `src/ingest/openstates.py` |

---

## A — LocalView (deliberation)

| | |
|---|---|
| **What** | US local government meeting videos + transcripts (YouTube-sourced) |
| **Dataset** | LocalView Public Meetings Database — DOI [`10.7910/DVN/NJTBEM`](https://doi.org/10.7910/DVN/NJTBEM) |
| **Replication code** | DOI [`10.7910/DVN/KHUXIN`](https://doi.org/10.7910/DVN/KHUXIN) |
| **Public files** | `codebook.md` (small); `meta_localview.parquet` (~35 MB); transcript tarballs ~2 GB × 3 |
| **Codebook download** | `https://dataverse.harvard.edu/api/access/datafile/14077924` |
| **Geo** | `st_fips` / place names in codebook — crosswalk to county FIPS in phase 1 |
| **Fetcher** | `src/ingest/localview.py` |
| **Sample on disk** | `data/raw/localview/codebook.md`; `meta_localview.parquet` (~35 MB) |
| **Not mirrored** | Full transcript tarballs (multi-GB); download on demand |

Bias (from spec): places that record meetings skew larger / richer / more urban.

---

## F — Arctic Shift / Reddit (vernacular)

| | |
|---|---|
| **What** | Historical Reddit dumps (submissions / comments) for backfill |
| **Repo** | https://github.com/ArthurHeitmann/arctic_shift |
| **Download links** | https://github.com/ArthurHeitmann/arctic_shift/blob/master/download_links.md |
| **Access** | Free torrents (Academic Torrents) + optional HTTP/API helpers; **no Reddit API key for dumps** |
| **Ongoing** | Official Reddit API for live pulls (OAuth; separate from dumps) |
| **Fetcher** | `src/ingest/arctic_shift.py` (notes only; dumps too large for scaffold) |
| **Blocker** | Multi-GB/TB torrents — document URL, do not auto-mirror |

Crosswalk city / regional subreddits → county FIPS is a separate geo table (not shipped yet).

---

## G — Project ledger / denominators

### EIA Form 861 (utilities / sales / territory)

| | |
|---|---|
| **What** | Annual electric power industry report — utility, sales, service territory |
| **Portal** | https://www.eia.gov/electricity/data/eia861/ |
| **2024 zip** | `https://www.eia.gov/electricity/data/eia861/zip/f8612024.zip` |
| **Access** | Public domain, no key |
| **Fetcher** | `src/ingest/eia_861.py` |
| **Sample on disk** | `data/raw/eia/f8612024.zip` + extracted `Utility_Data_2024.xlsx` |

### LBNL Queued Up (interconnection queues)

| | |
|---|---|
| **What** | Generation / storage projects seeking transmission interconnection |
| **Portal** | https://emp.lbl.gov/queues (Queued Up editions) |
| **Access** | Free spreadsheet releases (check current edition page for XLSX) |
| **Note** | Excludes load / distribution / behind-the-meter; not a national data-center permit registry |

### ISO / RTO queues & open data-center lists

Document per-ISO portals (PJM, MISO, CAISO, ERCOT, etc.) in manifests as they are wired. No national permit registry exists — coverage is whatever we build (spec failure mode G).

### Data Center Watch / opposition registries

Hand-curated cross-reference for layer E/G; not a free bulk API. Track as curated tables later.

---

## D — News (Media Cloud free; NewsBank paid)

| | |
|---|---|
| **Media Cloud** | Free research API with account + key; default weekly quota. Docs: https://www.mediacloud.org/ — Python: `pip install mediacloud` |
| **NewsBank Access World News** | **Paid / institutional** — same corpus BBD used for state EPU. **Do not depend on it for the free backbone.** |
| **Fetcher** | `src/ingest/media_cloud.py` (notes; requires `MC_API_KEY` to call) |

Layer D first external release is gated on NewsBank *if* local-paper density is required; Media Cloud can ship a thinner free series sooner.

---

## Geography crosswalk (Census)

| | |
|---|---|
| **What** | National counties gazetteer — USPS, GEOID (state+county FIPS), name, area, centroids |
| **2024 zip** | `https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_counties_national.zip` |
| **Access** | Public domain, no key |
| **On disk** | `data/raw/census/2024_Gaz_counties_national.txt` (3,222 counties + header) |
| **Helper** | `src/geo/fips.py` |

---

## H — Calibration (as published)

Pew, Gallup, AP-NORC national AI/tech series; ballot measures. Cite release pages; no automated free bulk assumed in scaffold.
