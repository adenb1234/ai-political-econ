# Free-source inventory (operational matrix)

**Access / verification date:** 2026-09-16 (PT).  
**Policy:** backbone uses **no paid APIs / no paid credits**. Do not invent empirical rows. Bulk raw stays under `data/raw/` (gitignored); manifests + this doc are the operational record.

**Canonical home:** this file is the tracker’s free-source status/readiness matrix (`docs/SOURCE_INVENTORY.md`). The merge source was the separate free-data workspace draft; all operational paths below are relative to this tracker repo.

**Companion docs:** narrative access URL notes in [`SOURCES.md`](SOURCES.md) · schema spine in [`WORKING_SPEC.md`](WORKING_SPEC.md) · taxonomy in [`TAXONOMY.md`](TAXONOMY.md) · CCC filter [`filters/ccc_ai_keywords_v0.md`](filters/ccc_ai_keywords_v0.md) (`ccc_rules_v0`).

**Spine keys every free ingest must hit:** `county_fips` (5-digit GEOID), `state` (USPS), `month` (`YYYY-MM`). Events also carry `event_date` / layer / taxonomy fields; panel is `PRIMARY KEY (county_fips, month)`.

**Layer free-status vocabulary:** `ready` · `blocked` · `already-have-raw`  
**Manifest / on-disk detail:** `downloaded` · `documented_only` · `blocked` · `codebook_downloaded` · `meta_downloaded`  
**FIPS × month crosswalk:** `ready` · `partial` · `not started`

Live URL checks used polite `curl` HEAD/GET from this box on **2026-09-16 PT**. Do not treat a 403 as “source gone” when login/Cloudflare is known.

Phase priority from working spec: **A → B → E** first, then **G**, then **F**. Layers C/D/H are notes-only for this free backbone (NewsBank **paid — excluded**).

---

## Per-layer free status summary (raw files and manifests checked on disk 2026-09-16 PT)

The required layer status is one of `ready`, `blocked`, or `already-have-raw`. Where a layer has both a verified raw input and documented follow-on sources, the layer status reflects the verified raw input; the detail rows below preserve the next-step distinction.

| Layer | Free status | Verified on-disk / manifest state | FIPS × month | Aden / paid blocker? |
|-------|-------------|-----------------------------------|--------------|----------------------|
| **A** Deliberation | **already-have-raw** | LocalView codebook + metadata downloaded; place→county crosswalk v0 + meta spine v0 on disk; transcripts deferred | `partial` (county + month on spine; unmatched keys 0; ambiguous keys remain) | None for free access |
| **B** Legislation | **blocked** | LegiScan raw empty; Open States documented only | `not started` | **Yes — free LegiScan bulk drop/key; optional Open States key** |
| **E** Mobilization | **already-have-raw** | CCC phase 3 downloaded; versioned transform outputs on disk | `partial` → matched rows checked | None for access |
| **F** Vernacular | **ready** | Arctic Shift and Google Trends documented only; no raw dumps | `not started` | Dump size, rate limits, and geo crosswalk |
| **G** Project ledger | **already-have-raw** | EIA-861 + LBNL Queued Up transforms v0 on disk (ix-queue activity ≠ DC permits); ISO/registries documented only | `partial` (LBNL/EIA v0) | No access blocker; ISO pick + DC permit curation remain |

Supplemental free options (Google Trends, hand-curated opposition registries, Media Cloud, and local RSS/HTML) are documented below without claiming unverified downloads. Census is a verified geography helper, not one of the five study layers.

---

## A — LocalView (deliberation) — **already-have-raw** (codebook + meta; transcripts deferred)

| Field | Detail |
|-------|--------|
| **Free status** | **already-have-raw** (codebook + meta + place→county crosswalk v0 + meta spine v0) |
| **Free access path** | Dataset DOI [10.7910/DVN/NJTBEM](https://doi.org/10.7910/DVN/NJTBEM). Codebook: `https://dataverse.harvard.edu/api/access/datafile/14077924`. Meta parquet (~35 MB): `https://dataverse.harvard.edu/api/access/datafile/14233652`. Transcripts: datafile ids `14233653`–`14233655` (~2 GB × 2 + ~1 GB). Replication code DOI [10.7910/DVN/KHUXIN](https://doi.org/10.7910/DVN/KHUXIN). |
| **License / ToS** | Harvard Dataverse / LocalView terms; cite DOI. Meeting-recording places skew larger / richer / more urban. |
| **Raw on disk** | **yes:** `data/raw/localview/codebook.md` (6,387 bytes; sha256 `f175fb1f…ec2f`) and `data/raw/localview/meta_localview.parquet` (35,339,621 bytes; sha256 `a7eccd0b…25f5` per `localview_meta.json`). Transcript tarballs remain deferred. |
| **Manifests** | `localview.json` (`meta_downloaded`), `localview_codebook.json`, `localview_meta.json` |
| **Processed (v0)** | Crosswalk: `data/processed/crosswalks/localview_place_to_county_v0.csv` (+ residuals CSV). **Meta spine:** `data/processed/localview/meta_spine_v0.parquet` (QA `…/localview_meta_spine_v0_qa.json`). **Entrypoint:** `python -m src.ingest.localview --include-meta` (or `make fetch-localview-meta`) fetches meta and builds crosswalk+spine; or `make crosswalk-localview` / `make spine-localview`. Transforms: `src/transform/localview_geo.py`, `localview_meta_spine.py`. |
| **Geo / FIPS** | **`partial`.** Place→county crosswalk v0 + meta spine v0 shipped (CT town→COG + name-alias + ANSI 2020 place_by_county fallbacks). Spine QA (2026-09-16 PT): 301,659 meta rows; matched county 269,264 (89.26%); ambiguous 32,395; unmatched 0; month ok 281,074 / fail 20,585; spine-ready 251,210 (83.28%). Residuals (ambiguous only): `data/processed/crosswalks/localview_place_to_county_v0_residuals.csv`. See `docs/notes/localview_meta_geo_v0.md`. |
| **Next free step** | Human-review 110 ambiguous/multi-county keys (32,395 meta rows). Optional panel rollup of meeting counts by `county_fips × month` once ambiguity policy is set. Do **not** pull transcript tarballs. |
| **Blockers** | None for free access. Transcript size (~5+ GB) is an ops choice, not a paywall. |

**Live check (2026-09-16 PT):** DOI `202`; codebook GET `200` / range `206`; meta HEAD `403` but range GET `206` — treat meta URL as reachable.

---

## B — Legislation (LegiScan + Open States) — **blocked**

### LegiScan (free bulk / free API)

| Field | Detail |
|-------|--------|
| **Free status** | **blocked** (login / free key / Cloudflare) |
| **Free access path** | Bulk portal https://legiscan.com/datasets (account required for ZIP). API https://api.legiscan.com/ (free key, rate-limited; env `LEGISCAN_API_KEY`). |
| **License / ToS** | LegiScan terms; attribution required. Introduced ≠ enacted; person records = *current* district/party. |
| **Raw on disk** | **no** — `data/raw/legiscan/` empty (`.gitkeep` only). |
| **Manifest** | `legiscan.json`: `portal_http_status` 403, `api_key_present` false, `local_files` []. |
| **Geo / FIPS** | **`not started`.** Need bill intro/action dates → `month`, plus sponsor/district → county (or state-only with QA exception). |
| **Next free step** | Aden creates a **free** LegiScan account, downloads **one** state (or Congress) bulk ZIP manually, drops under `data/raw/legiscan/`, **or** sets free `LEGISCAN_API_KEY` for a rate-limited probe. **Do not burn paid credits.** |
| **Blockers (Aden)** | Bulk portal Cloudflare/login **403** from this box; no free API key configured. |

**Live check (2026-09-16 PT):** datasets → **403**; API root → **403** (expected without session/key).

### Open States

| Field | Detail |
|-------|--------|
| **Free status** | **blocked** (optional vs LegiScan for phase 1) |
| **Free access path** | Docs https://docs.openstates.org/ — REST/GraphQL; production needs `OPENSTATES_API_KEY`. No credential-free national bill dump mirrored. |
| **License / ToS** | Open States terms / CC depending on endpoint. |
| **Raw on disk** | **no** — `data/raw/openstates/` empty. |
| **Manifest** | `openstates.json`, `api_key_present` false. |
| **Geo / FIPS** | **`not started`.** |
| **Next free step** | After LegiScan unblocks, register free Open States key only if committee fields are needed; otherwise defer. |
| **Blockers (Aden)** | No `OPENSTATES_API_KEY`. |

**Live check (2026-09-16 PT):** docs site **200**.

---

## E — Crowd Counting Consortium (mobilization) — **already-have-raw** (+ transform v0)

| Field | Detail |
|-------|--------|
| **Free status** | **already-have-raw**; keyword transform to `events`/`panel` already run (`ccc_rules_v0`) |
| **Free access path** | Phase 3 DOI [10.7910/DVN/RI9JFU](https://doi.org/10.7910/DVN/RI9JFU); direct `https://dataverse.harvard.edu/api/access/datafile/14226873` (`ccc-phase3-public.csv`). Phase 2 DOI [10.7910/DVN/9MMYDI](https://doi.org/10.7910/DVN/9MMYDI). Project: https://ash.harvard.edu/programs/crowd-counting-consortium/ |
| **License / ToS** | Harvard Dataverse / CCC terms; cite DOI. |
| **Raw on disk** | **yes:** `data/raw/ccc/ccc-phase3-public.csv` (47,231,658 bytes; sha256 `70253a0e…b621` per `ccc_phase3.json`; 65,232 lines / QA `total_ccc_rows` 63,147). |
| **Manifest** | `ccc_phase3.json` (`downloaded`) |
| **Processed (v0)** | `data/processed/events/ccc_ai_related_v0.csv` + `.jsonl` (98 matched); `data/processed/panel/ccc_mobilization_counts_v0.csv` (91 panel rows); QA `data/processed/qa/ccc_ai_related_v0_qa.json` (`missing_fips_among_matched: 0`). Filter doc: `docs/filters/ccc_ai_keywords_v0.md`; transform: `src/transform/ccc_to_events.py`. |
| **Geo / FIPS** | **`partial` upstream; matched v0 rows OK.** Many raw rows carry `fips_code`; QA reports zero missing FIPS among matched. |
| **Next free step** | Optional — pull CCC phase-2 public file for 2021–2024 backfill when expanding E history; refine `ccc_rules_v0` only if coverage gaps matter — do not invent filters. |
| **Blockers** | None for free download. |

**Live check (2026-09-16 PT):** datafile GET **200**; project page **200**.

---

## F — Vernacular (Arctic Shift / Reddit) — **ready** (documented; no dump)

| Field | Detail |
|-------|--------|
| **Free status** | **ready** to plan selective dump; **not** on disk (by design) |
| **Free access path** | Repo https://github.com/ArthurHeitmann/arctic_shift · links https://github.com/ArthurHeitmann/arctic_shift/blob/master/download_links.md — Academic Torrents + optional HTTP. **No Reddit API key for dumps.** Live Reddit OAuth is separate. |
| **License / ToS** | Upstream dump terms; posters ≠ city sample. |
| **Raw on disk** | **no dumps** — only `data/raw/arctic_shift/ACCESS.md`. |
| **Manifest** | `arctic_shift.json` (`documented_only`) |
| **Geo / FIPS** | **`not started`.** City/regional subreddit → county FIPS crosswalk **not shipped**; post `created_utc` → `YYYY-MM`. |
| **Next free step** | After A/B/E: pick smallest keyword-relevant dump slice from `download_links.md`; document URL in manifest before any pull. |
| **Blockers** | Multi-GB/TB size — do not auto-mirror. Disk/time decision for Aden/ops. |

**Live check (2026-09-16 PT):** repo **200**; `download_links.md` **200**.

### Google Trends (free complement; documented)

| Field | Detail |
|-------|--------|
| **Layer** | F (adjunct) |
| **Free status** | **ready** to pilot state-level pulls with polite backoff; no raw yet |
| **Free access path** | https://trends.google.com/trends/ — **no paid API**. Free clients: browser export or community libraries (e.g. `pytrends`) with **strict backoff**. Prefer DMA/metro or state series first; never hammer endpoints. |
| **License / ToS** | Google Terms of Service; Trends is a **relative** index (not absolute volume); scraping aggressively can get blocked — stay polite. |
| **On-disk / manifest** | **`documented_only`.** No Trends raw under `data/raw/` yet; no dedicated manifest file in scaffold. |
| **FIPS × month** | **`not started` / hard.** Native geography is often DMA or state, not county. County panel needs an explicit DMA→county crosswalk before spine join — treat as **partial at best** even after pulls. |
| **Next free ingest step** | Draft a tiny keyword list (AI / data center / local power) + state-level monthly pull script with sleep/backoff; store CSV under `data/raw/trends/` (gitignored) and add `data/manifests/google_trends.json`. |
| **Blockers** | Rate limits / ToS risk if impolite; DMA→county crosswalk design. **No paid Trends API.** |

**Live check (2026-09-16 PT):** Trends homepage **200**.

---

## G — Project ledger / denominators — **already-have-raw** (EIA) / **ready** for more free files

### EIA Form 861

| Field | Detail |
|-------|--------|
| **Free status** | **already-have-raw** |
| **Free access path** | Portal https://www.eia.gov/electricity/data/eia861/ · 2024 zip `https://www.eia.gov/electricity/data/eia861/zip/f8612024.zip` |
| **License / ToS** | US government work / public domain. |
| **Raw on disk** | **yes:** `data/raw/eia/f8612024.zip` (4,568,208 bytes; sha256 `77ce49c6…54de` per `eia_861_2024.json`) + extracted `Service_Territory_2024.xlsx` (440,753) + `Utility_Data_2024.xlsx` (260,483). |
| **Manifest** | `eia_861_2024.json` |
| **Geo / FIPS** | **`partial` → utility→county v0.** `src/transform/eia_861_to_coverage.py` / `make transform-eia`: Service Territory county names → Census FIPS (match_rate **0.9961**; 11,730/11,776); ambiguous county-vs-city + CT legacy + some AK historical areas left without FIPS (never invented). Grain remains **annual**, not county×month. |
| **Processed (v0)** | Crosswalk `data/processed/crosswalks/eia_861_utility_county_v0.csv`; utility/state stub `data/processed/panel/eia_861_utility_state_v0.csv` (1,701 rows); sample `…/eia_861_utility_county_v0_sample.csv`; QA `data/processed/qa/eia_861_coverage_v0_qa.json`. Notes: `docs/notes/g_eia_lbnl_v0.md`. |
| **Next free step** | Optional CT legacy→COG map; decide whether annual utility coverage joins the monthly panel as a slow-moving covariate. |
| **Blockers** | None for access. CT / city-county ambiguity documented in QA. |

**Live check (2026-09-16 PT):** portal HEAD **503** / GET **200** (treat as up); 2024 zip HEAD **200**.

### LBNL Queued Up (current edition)

| Field | Detail |
|-------|--------|
| **Free status** | **already-have-raw** |
| **Free access path** | Portal https://emp.lbl.gov/queues · 2026 Edition https://emp.lbl.gov/publications/queued-2026-edition-characteristics · Excel: `https://emp.lbl.gov/sites/default/files/2026-05/LBNL_Ix_Queue_Data_File_thru2025.xlsx` (~15.6 MB). |
| **License / ToS** | **CC BY 4.0** — attribute LBNL and GridTracker. Generation/storage queues — **not** load / data-center permit registry. |
| **Raw on disk** | **yes:** `data/raw/lbnl/LBNL_Ix_Queue_Data_File_thru2025.xlsx` (15,571,236 bytes; sha256 `794582d3…08b6`; access date PT 2026-09-16). Fetcher: `src/ingest/lbnl_queued_up.py` / `make fetch-lbnl`. |
| **Manifest** | `lbnl_queued_up_2026.json` (`downloaded`; notes explicitly exclude data-center permit counts). |
| **Geo / FIPS** | **`partial` → county×month v0.** `src/transform/lbnl_queue_to_panel.py` / `make transform-lbnl` on sheet `03. Complete Queue Data`: upstream `fips_code` → `county_fips` (coverage_fips_share **0.9509**; 36,325/38,201); month from `q_date` (coverage_month_share **0.9969**). Metric = **generation/storage interconnection queue activity** — **not** DC proposed/approved/denied. |
| **Processed (v0)** | County×month `data/processed/panel/lbnl_ix_queue_activity_v0.csv` (23,699 rows); state×month `…_state_month_v0.csv` (7,311); sample `…_v0_sample.csv`; QA `data/processed/qa/lbnl_ix_queue_activity_v0_qa.json`. |
| **Next free step** | Keep labels honest in any panel join; optionally pick one ISO for load/DC-adjacent queues (still not a national DC permit registry). |
| **Blockers** | None for free access. |

**Live check (2026-09-16 PT):** portal / publication / XLSX HEAD **200** (`content-length` 15571236).

### Major ISO / RTO open queue portals

| Field | Detail |
|-------|--------|
| **Layer** | G |
| **Free access path** | Per-ISO public landing pages (schemas differ). Indexed in `project_ledger_sources.json`. |
| **License / ToS** | Per-ISO terms; free viewing / sometimes free registration for downloads — read each portal before bulk pull. |
| **On-disk / manifest** | **`documented_only`.** No per-ISO raw pulls in scaffold. |
| **FIPS × month** | **`not started`.** Need project lat/long or county fields + queue status dates; coverage incomplete for data-center **load**. |
| **Next free ingest step** | Pick **one** ISO (recommend PJM or MISO); document the exact open CSV/XLSX download URL + column dictionary in a dedicated manifest **before** fetching. |
| **Blockers** | Engineering time / heterogeneous schemas. Some downloads may require free registration (not verified beyond landing-page HTTP status). |

Public entry pages re-checked with curl HEAD/GET on **2026-09-16 PT** (UA `ai-backlash-tracker-inventory/0.1`):

| ISO/RTO | Public page | HTTP | Notes |
|---------|-------------|------|-------|
| **PJM** | https://www.pjm.com/planning/services-requests/interconnection-queues.aspx | **200** | Also `…/service-requests/planning-queues` **200** |
| **MISO** | https://www.misoenergy.org/planning/generator-interconnection/ | **200** | Generator interconnection hub |
| **CAISO** | https://www.caiso.com/planning/Pages/GeneratorInterconnection/Default.aspx | **200** | Lowercase `/pages/generatorinterconnection` → **404**; use PascalCase path |
| **ERCOT** | https://www.ercot.com/gridinfo/resource | **200** | Resource / grid info (queue extracts vary by product) |
| **NYISO** | https://www.nyiso.com/interconnections | **200** | Interconnections portal |
| **ISO-NE** | https://www.iso-ne.com/system-planning/interconnection-service/ | **200** | Interconnection service |
| **SPP** | https://www.spp.org/engineering/generator-interconnection/ | **200** | Generator interconnection |

**Coverage caveat:** **no national data-center permit registry exists** (WORKING_SPEC failure mode G). Generation interconnection queues ≠ load / data-center permits.

### Opposition registries / Data Center Watch–style sources (hand-curated)

| Field | Detail |
|-------|--------|
| **Layer** | G (cross-ref E) |
| **Free access path** | No free bulk national API. Public editorial/watch pointers verified reachable: https://www.datacenterwatch.org/ (**200**), https://datacenterwatch.org/ (**200**). Trade press example (not a registry): https://www.datacenterknowledge.com/ (**200**). Treat as **pointers for hand curation**, not scrapable ground truth. |
| **License / ToS** | Site ToS; no redistribution of full site databases assumed. Cite pages; prefer link + date + county annotation in a curated table we own. |
| **On-disk / manifest** | **`documented_only` / hand-curated.** No invented opposition counts. Future curated CSV under something like `data/curated/opposition_registry.csv` (**not** created in this commit). |
| **FIPS × month** | **`not started`.** Curators must assign `county_fips` + `month` (first public opposition signal / hearing / lawsuit filing, etc.) per WORKING_SPEC event rules. |
| **Next free ingest step** | Define a 5–10 column curated schema (project name, county_fips, state, month, stance, source_url, access_date) and add empty template + README — **zero fabricated rows**. |
| **Blockers (Aden)** | Decide which watch/list sources are in-scope for citation; confirm no ToS scrape of login walls. |

---

## D — News (Media Cloud free; local RSS/HTML; NewsBank excluded)

### Media Cloud (free research tier)

| Field | Detail |
|-------|--------|
| **Layer** | D |
| **Free access path** | https://www.mediacloud.org/ — free research account + API key (`MC_API_KEY`). Python: `pip install mediacloud`. Notes: `data/raw/media_cloud/ACCESS.md`; fetcher `src/ingest/media_cloud.py`. |
| **License / ToS** | Media Cloud terms; attribution as required. Default weekly quota — confirm current FAQ before probing. |
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

## Geography crosswalk (Census) — **already-have-raw**

| Field | Detail |
|-------|--------|
| **Free access** | Counties: `…/2024_Gaz_counties_national.zip`. Places: `…/2024_Gaz_place_national.zip`. Place→county names: `https://www2.census.gov/geo/docs/reference/codes/files/national_places.txt`. Place×county FIPS: `https://www2.census.gov/geo/docs/reference/codes2020/national_place_by_county2020.txt`. CT town→2022 planning-region COGs: [CT Data Collaborative](https://github.com/CT-Data-Collaborative/ct-town-to-planning-region) (MIT; derived from Census TIGER). Public domain Census + MIT CT table. |
| **Raw on disk** | Counties TXT (647,830 bytes; sha256 `0a121d13…4451`) + Places TXT (6,499,209 bytes) + `national_places.txt` (2,803,570 bytes) + `national_place_by_county2020.txt` (2,736,928 bytes; sha256 `9996494d…06ec6`; access 2026-09-16 PT) + `ct_town_to_planning_region.csv` (11,988 bytes; access 2026-09-16 PT). |
| **Manifests** | `census_gaz_counties_2024.json`, `census_gaz_places_2024.json`, `census_national_places.json`, `census_place_by_county_2020.json`, `census_ct_town_to_planning_region.json` |
| **Helpers** | `src/geo/fips.py`; LocalView join `src/transform/localview_geo.py` (`make crosswalk-localview`) |
| **FIPS × month** | **`ready`** for county universe / USPS↔GEOID joins (month not in gazetteer). Place→county for LocalView v0 on disk. |

---

## H — Calibration (as published)

Pew, Gallup, AP-NORC national AI/tech series and ballot measures: **cite release pages**; no automated free bulk assumed. Not part of free county×month backbone ingest this phase.

---

## Exact next free ingest actions (priority A→B→E)

1. **A:** Meta spine v0 landed (`python -m src.ingest.localview --include-meta`; 251,210 spine-ready / 83.28%; unmatched county keys 0). **Next:** human-review ambiguous/multi-county keys (32,395 rows; 110 place keys); optional `county_fips × month` meeting-count panel. No transcript tarballs.
2. **E:** Already past raw + `ccc_rules_v0` transform; optional phase-2 CCC backfill later.
3. **G:** LBNL ix-queue county×month + EIA-861 utility→county v0 landed (`make transform-g`). Optionally pick one ISO next; do not invent DC permit counts.
4. **B:** Unblock only after Aden free LegiScan drop or free API key.
5. **F/D:** Defer Arctic Shift torrents / Media Cloud until keys + disk plan exist.

---

## Blockers needing Aden / paid access

| ID | Blocker | Needed action |
|----|---------|---------------|
| B1 | LegiScan portal/API **403**; empty `data/raw/legiscan/` | Free account bulk ZIP drop **or** free `LEGISCAN_API_KEY` (**no paid tier**) |
| B2 | No `OPENSTATES_API_KEY` | Optional; set only if committee detail required |
| D1 | No `MC_API_KEY` | Free Media Cloud account for thinner layer D |
| D2 | NewsBank | Keep **excluded** (paid/institutional) |
| F1 | Arctic Shift torrent size (multi-GB/TB) | Approve selective dump + disk budget before mirror |
| F2 | Google Trends DMA→county | Accept state/DMA grain for early F, or fund crosswalk design |
| G1 | No national DC permit registry | Accept hand-built ledger coverage (spec failure mode G) |
| G2 | Opposition registries | Approve curated schema + which sites may be cited (no login-wall scrapes) |
| Ops | GitHub remote missing | Local `.git` only (`git remote` empty) — create private remote when ready; **do not push from this agent** |

---

## Git / dump policy

- Tracker `.gitignore` excludes large `data/raw/**` formats. Keep **manifests** in git; keep **dumps** on disk only.
- Prefer a **single** raw copy under this repo’s `data/raw/` (do not duplicate into free-data workspace).
- Free-data workspace at `/workspace/ai-backlash-free-data` is notes-only (no `.git`); do not `git init` it.

---

## Verification log

**Verified on disk 2026-09-16 PT (ls sizes + sha256sum where checked):** CCC CSV 47,231,658 bytes / sha256 matches manifest; LocalView codebook 6,387 plus metadata parquet 35,339,621 bytes / sha256 matches manifests; EIA zip 4,568,208 / sha256 matches; Census txt 647,830 / sha256 matches; LegiScan/Open States/Arctic Shift raw empty or ACCESS-only; CCC processed events/panel/QA present as above. **Later same day PT:** Census places gaz + `national_places.txt` downloaded; LocalView place→county crosswalk v0 QA (1,150 keys; 1,038 matched / 0.9026; meta-row match 0.8917; unmatched keys 2 / 263 rows); LocalView meta spine v0 (`data/processed/localview/meta_spine_v0.parquet`) QA: matched 269,001 / ambiguous 32,395 / unmatched 263; month ok 281,074 / fail 20,585; spine-ready 251,070; CT town→COG CSV 11,988 bytes / sha256 `4592692e…11a9`; LBNL Queued Up XLSX 15,571,236 bytes / sha256 `794582d3…08b6`. **Still later 2026-09-16 PT:** CT town→COG CSV + name-alias fallbacks rebuilt crosswalk (keys matched 1,038 / 0.9026; meta-row match 269,001 / 0.8917; unmatched keys 2); spine-ready 251,070 / 0.8323; residuals CSV on disk. **Same day PT (place_by_county_2020):** ANSI `national_place_by_county2020.txt` 2,736,928 / sha256 `9996494d…06ec6`; Semmes AL + Brookhaven GA matched; crosswalk keys 1,040 / 0.9043; meta matched 269,264 / 0.8926; unmatched keys **0**; spine-ready 251,210 / 0.8328. **G transform pass 2026-09-16 PT (evening):** LBNL `lbnl_ix_queue_v0` total_queue_rows 38,201; with_county_fips 36,325 (0.9509); month_parseable 38,084 (0.9969); panel_county_month_rows 23,699; panel_state_month_rows 7,311. EIA `eia_861_coverage_v0` territory_rows 11,776; matched_fips 11,730 (0.9961); ambiguous 11; unmatched 35 (CT legacy + AK historical + residual spellings); utility_state_rows 1,701. Schema freeze: events.sql / panel.sql / taxonomy untouched.

**Verified live with curl 2026-09-16 PT (this pass):** LBNL Queued Up portal + 2026 publication page + XLSX HEAD **200** (`content-length` 15571236); EIA portal HEAD **503**/GET **200**, zip **200**; LegiScan datasets + API **403**; Open States docs **200**; Arctic Shift repo + download_links **200**; Google Trends **200**; Media Cloud **200**; Census gazetteer zip **200**; CCC project page **200** / Dataverse datafile HEAD **403** (file already on disk; range GET pattern works for LocalView meta **206**); PJM/MISO/CAISO(PascalCase)/ERCOT/NYISO/ISO-NE/SPP landing pages **200** (CAISO lowercase path **404**); datacenterwatch.org + datacenterknowledge.com **200**.

**Reconciled from:** `SOURCES.md`, `data/manifests/*.json`, on-disk `data/raw/**` / `data/processed/**`, and draft inventory formerly at `/workspace/ai-backlash-free-data/docs/SOURCE_INVENTORY.md`.
