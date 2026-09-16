# Free-source inventory (operational matrix)

**Access date:** 2026-09-16 (PT).  
**Policy:** backbone uses **no paid APIs / no paid credits**. Do not invent empirical rows. Bulk raw stays under `data/raw/` (gitignored); manifests + this doc are the operational record.

**Companion docs:** narrative access notes in [`SOURCES.md`](SOURCES.md) · schema spine in [`WORKING_SPEC.md`](WORKING_SPEC.md) · taxonomy in [`TAXONOMY.md`](TAXONOMY.md).

**Spine keys every free ingest must hit:** `county_fips` (5-digit GEOID), `state` (USPS), `month` (`YYYY-MM`). Events also carry `event_date` / layer / taxonomy fields; panel is `PRIMARY KEY (county_fips, month)`.

**Status vocabulary (on-disk / manifest):** `downloaded` · `documented_only` · `blocked`  
**Crosswalk vocabulary:** `ready` · `partial` · `not started`

Live URL checks below used polite `curl` HEAD/GET from this box on **2026-09-16 PT** (User-Agent `ai-backlash-tracker-inventory/0.1`). Do not treat a 403 as “source gone” when login/Cloudflare is known.

---

## Status rollup

| Layer | Source | On-disk / manifest | FIPS × month | Blocker? |
|-------|--------|--------------------|--------------|----------|
| A | LocalView | codebook `downloaded`; meta/transcripts `documented_only` | `partial` | Size for transcripts only |
| B | LegiScan free bulk/API | `blocked` / `documented_only` | `not started` | **Yes — Aden** (login / free key) |
| B | Open States | `documented_only` | `not started` | **Yes — Aden** (free API key) |
| D | Media Cloud free | `documented_only` | `not started` | **Yes — Aden** (`MC_API_KEY`) |
| D | Local media RSS/HTML | policy only | `not started` | Legal/ToS per site |
| E | CCC phase 3 | `downloaded` | `partial` (many rows have `fips_code`) | Filter design (not access) |
| F | Arctic Shift / Reddit dumps | `documented_only` | `not started` | **Torrent size** |
| F | Google Trends | `documented_only` | `not started` | Rate limits / DMA→county |
| G | EIA Form 861 | `downloaded` | `partial` (utility→county TBD) | None for access |
| G | LBNL Queued Up 2026 | `documented_only` (URL verified) | `partial` (county maps exist upstream) | None for access |
| G | ISO/RTO queue portals | `documented_only` (pages verified) | `not started` | Schema glue per ISO |
| G | Opposition registries | hand-curated only | `not started` | Manual curation |
| geo | Census 2024 counties gazetteer | `downloaded` | `ready` (spine helper) | None |
| H | Pew/Gallup/AP-NORC/ballots | cite-as-published | n/a national | No free bulk assumed |

---

## A — LocalView (deliberation)

| Field | Detail |
|-------|--------|
| **Layer** | A |
| **Free access path** | Dataset DOI [10.7910/DVN/NJTBEM](https://doi.org/10.7910/DVN/NJTBEM). Codebook: `https://dataverse.harvard.edu/api/access/datafile/14077924`. Meta parquet (~35 MB): `https://dataverse.harvard.edu/api/access/datafile/14233652`. Transcripts: datafile ids `14233653`–`14233655` (~2 GB × 2 + ~1 GB). Replication code DOI [10.7910/DVN/KHUXIN](https://doi.org/10.7910/DVN/KHUXIN). |
| **License / ToS** | Harvard Dataverse / LocalView terms; cite DOI. Meeting-recording places skew larger / richer / more urban. |
| **On-disk / manifest** | **Partial downloaded.** `data/raw/localview/codebook.md` present; manifests `localview.json`, `localview_codebook.json`. Meta parquet + transcript tarballs **not** mirrored (by design). |
| **FIPS × month** | **`partial`.** Codebook documents `st_fips` / place names; county FIPS crosswalk + meeting-date → `YYYY-MM` still TBD. |
| **Next free ingest step** | From tracker root: `python -m src.ingest.localview --include-meta` → land `meta_localview.parquet` only (do **not** pull transcript tarballs in that step). |
| **Blockers** | None for free access. Transcript size (~5+ GB) is an ops choice, not a paywall. |

**Live check (2026-09-16 PT):** DOI `202`; codebook GET `200` / range `206`; meta HEAD `403` but range GET `206` (octet-stream) — treat meta URL as reachable.

---

## B — Legislation (LegiScan + Open States)

### LegiScan (free bulk / free API)

| Field | Detail |
|-------|--------|
| **Layer** | B |
| **Free access path** | Bulk portal https://legiscan.com/datasets (account required for ZIP). API https://api.legiscan.com/ (free key, rate-limited; env `LEGISCAN_API_KEY`). |
| **License / ToS** | LegiScan terms; attribution required. Introduced ≠ enacted; person records = *current* district/party. |
| **On-disk / manifest** | **`blocked` / `documented_only`.** `data/raw/legiscan/` empty (`.gitkeep` only). Manifest `legiscan.json`: `portal_http_status` 403, `api_key_present` false. |
| **FIPS × month** | **`not started`.** Need bill intro/action dates → `month`, plus sponsor/district → county (or state-only with QA exception until geo table exists). |
| **Next free ingest step** | Aden creates a **free** LegiScan account, downloads **one** state (or Congress) bulk ZIP manually, drops it under `data/raw/legiscan/`, **or** sets free `LEGISCAN_API_KEY` for a rate-limited probe. |
| **Blockers (Aden)** | **LegiScan bulk portal Cloudflare/login HTTP 403 from this box; no free API key configured.** Do not use paid LegiScan tiers. |

**Live check (2026-09-16 PT):** `https://legiscan.com/datasets` → **403**; `https://api.legiscan.com/` → **403** (expected without session/key).

### Open States

| Field | Detail |
|-------|--------|
| **Layer** | B |
| **Free access path** | Docs https://docs.openstates.org/ — REST/GraphQL; production use needs API key (`OPENSTATES_API_KEY`). No credential-free national bill dump mirrored here. |
| **License / ToS** | Open States terms / CC depending on endpoint. |
| **On-disk / manifest** | **`documented_only`.** `data/raw/openstates/` empty; manifest `openstates.json`, `api_key_present` false. |
| **FIPS × month** | **`not started`.** Same date/geo gaps as LegiScan; useful for committee detail complement. |
| **Next free ingest step** | After LegiScan path unblocks, register free Open States key only if committee fields are needed; otherwise defer. |
| **Blockers (Aden)** | **No `OPENSTATES_API_KEY`.** Optional vs LegiScan for phase 1. |

**Live check (2026-09-16 PT):** docs site **200**.

---

## E — Crowd Counting Consortium (mobilization)

| Field | Detail |
|-------|--------|
| **Layer** | E |
| **Free access path** | Phase 3 DOI [10.7910/DVN/RI9JFU](https://doi.org/10.7910/DVN/RI9JFU); direct file `https://dataverse.harvard.edu/api/access/datafile/14226873` (`ccc-phase3-public.csv`). Phase 2 DOI [10.7910/DVN/9MMYDI](https://doi.org/10.7910/DVN/9MMYDI). Project: https://ash.harvard.edu/programs/crowd-counting-consortium/ · Dataverse root: https://dataverse.harvard.edu/dataverse/crowdcountingconsortium |
| **License / ToS** | Harvard Dataverse / CCC terms; cite DOI. |
| **On-disk / manifest** | **`downloaded`.** `data/raw/ccc/ccc-phase3-public.csv` (~47 MB, ~65k rows); manifest `ccc_phase3.json` (sha256 recorded). Fetcher `src/ingest/ccc.py`. |
| **FIPS × month** | **`partial`.** Many rows already carry `fips_code` (5-digit); event date → `month` is straightforward. Rows missing FIPS need locality/state QA. Downstream AI/data-center/energy filter via `claims_*` / `issue_tags_*` / `organizations` — do not invent filter hits here. |
| **Next free ingest step** | Probe share of rows with usable `fips_code`; run/extend CCC→events transform + versioned keyword filter (see `src/transform/` if present) into `events` layer E. |
| **Blockers** | None for free download. Filter/taxonomy mapping is research design, not access. |

**Live check (2026-09-16 PT):** datafile GET **200**; project page **200**.

---

## F — Vernacular (Arctic Shift / Reddit + Google Trends)

### Arctic Shift (historical Reddit dumps)

| Field | Detail |
|-------|--------|
| **Layer** | F |
| **Free access path** | Repo https://github.com/ArthurHeitmann/arctic_shift · download index https://github.com/ArthurHeitmann/arctic_shift/blob/master/download_links.md — Academic Torrents + optional HTTP. **No Reddit API key for dumps.** Live Reddit API (OAuth) is separate and out of this free-dump path. |
| **License / ToS** | Upstream dump terms; posters ≠ city sample. |
| **On-disk / manifest** | **`documented_only`.** `data/raw/arctic_shift/ACCESS.md` only; manifest `arctic_shift.json`. No dumps mirrored. |
| **FIPS × month** | **`not started`.** Need city/regional subreddit → county FIPS geo table (not shipped) + post `created_utc` → `YYYY-MM`. |
| **Next free ingest step** | After A/B/E priority work: pick the **smallest** keyword-relevant dump slice from `download_links.md`; document chosen torrent/HTTP URL in manifest before any pull. |
| **Blockers** | **Multi-GB/TB torrent size — do not auto-mirror.** Disk + time decision for Aden/ops. |

**Live check (2026-09-16 PT):** repo **200**; `download_links.md` **200**.

### Google Trends (free; polite rate limits)

| Field | Detail |
|-------|--------|
| **Layer** | F (interest / vernacular complement) |
| **Free access path** | https://trends.google.com/trends/ — no paid API. Common free clients: browser export or community libraries (e.g. `pytrends`) with **strict backoff**. Prefer DMA/metro or state series first; never hammer endpoints. |
| **License / ToS** | Google Terms of Service; Trends is a relative index (not absolute volume); scraping aggressively can get blocked — stay polite. |
| **On-disk / manifest** | **`documented_only`.** No Trends raw under `data/raw/` yet; no dedicated manifest file in scaffold. |
| **FIPS × month** | **`not started` / hard.** Native geography is often DMA or state, not county. County panel needs an explicit DMA→county crosswalk (population-weighted or similar) before spine join — treat as **partial at best** even after pulls. |
| **Next free ingest step** | Draft a tiny keyword list (AI / data center / local power) + state-level monthly pull script with sleep/backoff; store CSV under `data/raw/trends/` (gitignored) and add `data/manifests/google_trends.json`. |
| **Blockers** | Rate limits / ToS risk if impolite; DMA→county crosswalk design. **No paid Trends API.** |

**Live check (2026-09-16 PT):** Trends homepage **200**.

---

## G — Project ledger / denominators

### EIA Form 861

| Field | Detail |
|-------|--------|
| **Layer** | G |
| **Free access path** | Portal https://www.eia.gov/electricity/data/eia861/ · 2024 zip `https://www.eia.gov/electricity/data/eia861/zip/f8612024.zip` |
| **License / ToS** | US government work / public domain. |
| **On-disk / manifest** | **`downloaded`.** `data/raw/eia/f8612024.zip` + extracted `Utility_Data_2024.xlsx`; manifest `eia_861_2024.json`. Fetcher `src/ingest/eia_861.py`. |
| **FIPS × month** | **`partial`.** Annual utility/territory tables — need utility service territory → county FIPS crosswalk; month grain is annual (broadcast to months or mark as year-constant denominator). |
| **Next free ingest step** | Map `Utility_Data_2024.xlsx` service-territory fields onto Census county FIPS using existing gazetteer helper (`src/geo/fips.py`). |
| **Blockers** | None for access. |

**Live check (2026-09-16 PT):** portal **200**; 2024 zip **200**.

### LBNL Queued Up (current edition)

| Field | Detail |
|-------|--------|
| **Layer** | G |
| **Free access path** | Portal https://emp.lbl.gov/queues · **2026 Edition** publication https://emp.lbl.gov/publications/queued-2026-edition-characteristics · **Excel (thru end-2025, updated May 2026):** `https://emp.lbl.gov/sites/default/files/2026-05/LBNL_Ix_Queue_Data_File_thru2025.xlsx` (~15.6 MB). County/region interactive maps: `/maps-projects-region-state-and-county` on emp.lbl.gov. |
| **License / ToS** | **CC BY 4.0** — attribute Lawrence Berkeley National Laboratory and GridTracker (stated on portal). Generation/storage interconnection queues — **not** load / data-center permit registry. |
| **On-disk / manifest** | **`documented_only`.** Indexed in `project_ledger_sources.json`; file not yet downloaded to `data/raw/`. |
| **FIPS × month** | **`partial`.** Upstream provides region/state/county map products; queue timestamps → `YYYY-MM` still need a transform plan. Do **not** invent proposed/approved/denied data-center counts from this file. |
| **Next free ingest step** | `curl`/fetcher download of `LBNL_Ix_Queue_Data_File_thru2025.xlsx` into `data/raw/lbnl/` + new manifest `lbnl_queued_up_2026.json` (sha256, bytes, access date). |
| **Blockers** | None for free access (URL verified without login). |

**Live check (2026-09-16 PT):** portal **200**; publication page **200**; XLSX HEAD **200** (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `content-length` 15571236).

### Major ISO / RTO open queue portals

Documented public entry pages (schemas differ; none is a national data-center permit registry). Manifest index: `project_ledger_sources.json`.

| ISO/RTO | Public page checked | HTTP (2026-09-16 PT) | Notes |
|---------|---------------------|----------------------|-------|
| **PJM** | https://www.pjm.com/planning/services-requests/interconnection-queues.aspx | **200** | Interconnection queues service page |
| **MISO** | https://www.misoenergy.org/planning/generator-interconnection/ | **200** | Generator interconnection hub |
| **CAISO** | https://www.caiso.com/planning/Pages/GeneratorInterconnection/Default.aspx | **200** | Generator interconnection landing (legacy path still served) |
| **ERCOT** | https://www.ercot.com/gridinfo/resource | **200** | Resource / grid info (queue extracts vary by product) |
| **NYISO** | https://www.nyiso.com/interconnections | **200** | Interconnections portal |
| **ISO-NE** | https://www.iso-ne.com/system-planning/interconnection-service/ | **200** | Interconnection service |
| **SPP** | https://www.spp.org/engineering/generator-interconnection/ | **200** | Generator interconnection |

| Field | Detail |
|-------|--------|
| **Layer** | G |
| **License / ToS** | Per-ISO terms; usually free viewing / registered downloads — read each portal before bulk pull. |
| **On-disk / manifest** | **`documented_only`** (URLs above). No per-ISO raw pulls in scaffold. |
| **FIPS × month** | **`not started`.** Need project lat/long or county fields + queue status dates; coverage incomplete for data-center **load**. |
| **Next free ingest step** | Pick **one** ISO (recommend PJM or MISO) and document the exact open CSV/XLSX download URL + column dictionary in a dedicated manifest before fetching. |
| **Blockers** | Engineering time / heterogeneous schemas. Some downloads may require free registration (not verified beyond landing-page 200). |

### Opposition registries / Data Center Watch–style sources (hand-curated)

| Field | Detail |
|-------|--------|
| **Layer** | G (cross-ref E) |
| **Free access path** | No free bulk national API. Public editorial/watch sites verified reachable: https://www.datacenterwatch.org/ (**200**), https://datacenterwatch.org/ (**200**). Trade press example (not a registry): https://www.datacenterknowledge.com/ (**200**). Treat as **pointers for hand curation**, not scrapable ground truth. |
| **License / ToS** | Site ToS; no redistribution of full site databases assumed. Cite pages; prefer link + date + county annotation in a curated table we own. |
| **On-disk / manifest** | **`documented_only` / hand-curated.** No invented opposition counts. Future curated CSV under something like `data/curated/opposition_registry.csv` (not created in this commit). |
| **FIPS × month** | **`not started`.** Curators must assign `county_fips` + `month` (first public opposition signal / hearing / lawsuit filing, etc.) per WORKING_SPEC event rules. |
| **Next free ingest step** | Define a 5–10 column curated schema (project name, county_fips, state, month, stance, source_url, access_date) and add empty template + README — **zero fabricated rows**. |
| **Blockers (Aden)** | Decide which watch/list sources are in-scope for citation; confirm no ToS scrape of login walls. |

---

## D — News (Media Cloud free; local RSS/HTML; NewsBank excluded)

### Media Cloud (free research tier)

| Field | Detail |
|-------|--------|
| **Layer** | D |
| **Free access path** | https://www.mediacloud.org/ — free research account + API key (`MC_API_KEY`). Python: `pip install mediacloud`. Default weekly quota (historically ~4k req/week — confirm current FAQ). Notes: `data/raw/media_cloud/ACCESS.md`; fetcher `src/ingest/media_cloud.py`. |
| **License / ToS** | Media Cloud terms; attribution as required. |
| **On-disk / manifest** | **`documented_only`.** Manifest `media_cloud.json`, `api_key_present` false. **NewsBank Access World News = paid — excluded from free backbone.** |
| **FIPS × month** | **`not started`.** Geocoding local outlets → county is non-trivial; start with state aggregates or known local-source lists. |
| **Next free ingest step** | Aden creates free Media Cloud account, sets `MC_API_KEY`, run a single keyword probe for one state-month (stay under quota). |
| **Blockers (Aden)** | **No `MC_API_KEY`.** Thinner free D series possible; dense local-paper D still gated on paid NewsBank if that density is required. |

**Live check (2026-09-16 PT):** mediacloud.org **200**.

### Local media RSS / HTML (policy only)

| Field | Detail |
|-------|--------|
| **Layer** | D |
| **Free access path** | Per-outlet public RSS feeds or openly linked HTML article indexes. **No scraping behind login walls, paywalls, or ToS-prohibited bots.** Prefer robots.txt-respecting feed URLs Aden or volunteers list. |
| **License / ToS** | Copyright remains with publisher; store URLs + metadata + short quotes under fair-use judgment — not full-text corpora in git. |
| **On-disk / manifest** | **Policy only** — no feed list committed yet. |
| **FIPS × month** | **`not started`.** Each outlet needs a home-county (or multi-county) assignment table. |
| **Next free ingest step** | Build a curated `local_media_feeds.json` (outlet, rss_url, state, primary_county_fips, license_note) with **zero** automated crawl until list exists. |
| **Blockers** | Legal/ToS per site; labor to curate feeds. |

---

## Geography crosswalk (Census) — all-layer helper

| Field | Detail |
|-------|--------|
| **Layer** | geo (supports A/B/E/F/G/D) |
| **Free access path** | `https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_counties_national.zip` |
| **License / ToS** | US government work / public domain. |
| **On-disk / manifest** | **`downloaded`.** `data/raw/census/2024_Gaz_counties_national.txt` (3,222 counties + header) + zip; manifest `census_gaz_counties_2024.json`. Helper `src/geo/fips.py`. |
| **FIPS × month** | **`ready`** for county universe / USPS↔GEOID joins. Month is not in the gazetteer (join key only). |
| **Next free ingest step** | Keep as dependency for place→county and utility-territory joins; no re-download needed unless Census publishes 2025+ gazetteer. |
| **Blockers** | None. |

**Live check (2026-09-16 PT):** zip **200**.

---

## H — Calibration (as published)

Pew, Gallup, AP-NORC national AI/tech series and ballot measures: **cite release pages**; no automated free bulk assumed in scaffold. Not part of free county×month backbone ingest this phase.

---

## Exact next free ingest actions (priority)

1. **A:** `python -m src.ingest.localview --include-meta` (meta parquet only).  
2. **E:** FIPS coverage probe + keyword filter → `events` (raw already on disk).  
3. **G:** Download LBNL Queued Up 2026 XLSX (URL above) + manifest.  
4. **B:** Unblock only after Aden free LegiScan drop or free API key.  
5. **F/D:** Defer Arctic Shift torrents / Media Cloud until keys + disk plan exist; Trends state-level pilot is free but rate-limit carefully.

---

## Blockers needing Aden / parent agent

| ID | Blocker | Needed decision / action |
|----|---------|--------------------------|
| B1 | **LegiScan portal/API 403** from box; empty `data/raw/legiscan/` | Free account bulk ZIP drop **or** free `LEGISCAN_API_KEY` (no paid tier) |
| B2 | **No `OPENSTATES_API_KEY`** | Optional; set only if committee detail required |
| D1 | **No `MC_API_KEY`** | Free Media Cloud account for thinner layer D |
| D2 | NewsBank | Keep **excluded** from free backbone (paid/institutional) |
| F1 | **Arctic Shift torrent size** (multi-GB/TB) | Approve selective dump + disk budget before any mirror |
| F2 | Google Trends DMA→county | Accept state/DMA grain for early F, or fund crosswalk design |
| G1 | No national DC permit registry | Accept hand-built ledger coverage (spec failure mode G) |
| G2 | Opposition registries | Approve curated schema + which sites may be cited (no login-wall scrapes) |
| Ops | **GitHub remote missing** | Tracker has local `.git` only (`git remote` empty) — create private remote when ready; **do not push from this agent** |
| Ops | Dirty `main` worktree | Leave other agents’ uncommitted `data/manifests/*` + `src/ingest/census_fips.py` alone |

---

## Verification log (what was checked live vs copied)

**Verified live with curl on 2026-09-16 PT:** LBNL Queued Up portal + 2026 publication page + XLSX URL; EIA portal + 2024 zip; CCC datafile + project page; LocalView DOI + codebook + meta (range GET); LegiScan datasets + API (**403**); Open States docs; Arctic Shift repo + download_links; Google Trends; Media Cloud; Census gazetteer zip; PJM, MISO, CAISO, ERCOT, NYISO, ISO-NE, SPP queue landing pages (**all 200**); datacenterwatch.org (**200**).

**Copied / reconciled from existing tracker docs + manifests (not re-derived as new empirics):** layer narratives in `SOURCES.md`; on-disk paths/bytes/sha256 from `data/manifests/*.json` and `data/raw/**` listing; LocalView transcript datafile ids; phase priority A→B→E; NewsBank exclusion; ACCESS.md notes for Arctic Shift / Media Cloud. Useful structure also merged from `/workspace/ai-backlash-free-data/docs/SOURCE_INVENTORY.md` (draft) into this tracker-canonical file.
