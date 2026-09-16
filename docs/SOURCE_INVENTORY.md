# Free-source inventory (operational matrix)

**Access / verification date:** 2026-09-16 (PT).  
**Policy:** backbone uses **no paid APIs / no paid credits**. Do not invent empirical rows. Bulk raw stays under `data/raw/` (gitignored); manifests + this doc are the operational record.

**Canonical home:** this file is the tracker’s free-source status/readiness matrix (`docs/SOURCE_INVENTORY.md`). A draft previously lived in `/workspace/ai-backlash-free-data/docs/SOURCE_INVENTORY.md`.

**Companion docs:** narrative access URL notes in [`SOURCES.md`](SOURCES.md) · schema spine in [`WORKING_SPEC.md`](WORKING_SPEC.md) · taxonomy in [`TAXONOMY.md`](TAXONOMY.md) · CCC filter [`filters/ccc_ai_keywords_v0.md`](filters/ccc_ai_keywords_v0.md) (`ccc_rules_v0`).

**Spine keys every free ingest must hit:** `county_fips` (5-digit GEOID), `state` (USPS), `month` (`YYYY-MM`). Events also carry `event_date` / layer / taxonomy fields; panel is `PRIMARY KEY (county_fips, month)`.

**Layer free-status vocabulary:** `ready` · `blocked` · `already-have-raw`  
**Manifest / on-disk detail:** `downloaded` · `documented_only` · `blocked` · `codebook_downloaded`  
**FIPS × month crosswalk:** `ready` · `partial` · `not started`

Live URL checks used polite `curl` HEAD/GET from this box on **2026-09-16 PT**. Do not treat a 403 as “source gone” when login/Cloudflare is known.

Phase priority from working spec: **A → B → E** first, then **G**, then **F**. Layers C/D/H are notes-only for this free backbone (NewsBank **paid — excluded**).

---

## Per-layer free status summary

| Layer | Free status | On-disk / manifest detail | FIPS × month | Aden / paid blocker? |
|-------|-------------|---------------------------|--------------|----------------------|
| **A** LocalView | **ready** (partial raw) | codebook `downloaded`; meta/transcripts `documented_only` | `partial` | None (transcript size is ops) |
| **B** LegiScan | **blocked** | `blocked` / `documented_only`; raw empty | `not started` | **Yes — free account bulk drop or free API key** |
| **B** Open States | **blocked** (optional) | `documented_only` | `not started` | **Yes — free API key** (defer vs LegiScan) |
| **E** CCC phase 3 | **already-have-raw** (+ transform v0) | `downloaded`; events/panel/QA on disk | `partial` → matched rows OK | None for access |
| **F** Arctic Shift | **ready** (documented; no dump) | `documented_only` | `not started` | Torrent size / disk budget |
| **G** EIA-861 | **already-have-raw** | `downloaded` | `partial` (utility→county TBD) | None |
| **G** LBNL / ISO / registries | **ready** (document-only) | `documented_only` | `partial` / `not started` | Hand-curation for opposition lists |
| geo Census gazetteer | **already-have-raw** | `downloaded` | `ready` (spine helper) | None |
| D Media Cloud | notes only | `documented_only` | `not started` | **`MC_API_KEY`**; NewsBank paid excluded |
| H Calibration | cite-as-published | n/a | n/a national | No free bulk assumed |

---

## A — LocalView (deliberation) — **ready** (partial raw)

| Field | Detail |
|-------|--------|
| **Free status** | **ready** for next free pull; codebook already on disk |
| **Free access path** | Dataset DOI [10.7910/DVN/NJTBEM](https://doi.org/10.7910/DVN/NJTBEM). Codebook: `https://dataverse.harvard.edu/api/access/datafile/14077924`. Meta parquet (~35 MB): `https://dataverse.harvard.edu/api/access/datafile/14233652`. Transcripts: datafile ids `14233653`–`14233655` (~2 GB × 2 + ~1 GB). Replication code DOI [10.7910/DVN/KHUXIN](https://doi.org/10.7910/DVN/KHUXIN). |
| **License / ToS** | Harvard Dataverse / LocalView terms; cite DOI. Meeting-recording places skew larger / richer / more urban. |
| **Raw on disk** | **yes (sample):** `data/raw/localview/codebook.md` (6,387 bytes; sha256 `f175fb1f…ec2f` per `localview_codebook.json`). Meta parquet + transcript tarballs **not** mirrored (by design). |
| **Manifests** | `localview.json` (`codebook_downloaded`), `localview_codebook.json` |
| **Geo / FIPS** | **`partial`.** Codebook documents `st_fips` / place names; county FIPS crosswalk + meeting-date → `YYYY-MM` still TBD. |
| **Next free step** | From tracker root: `python -m src.ingest.localview --include-meta` → land `meta_localview.parquet` only (do **not** pull transcript tarballs). |
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
| **Free status** | **ready** to pilot state-level pulls with backoff; no raw yet |
| **Free access path** | https://trends.google.com/trends/ — no paid API. Prefer polite browser export / community clients with strict backoff. |
| **License / ToS** | Google ToS; relative index; aggressive scraping can get blocked. |
| **Raw / manifest** | **documented only** — no Trends raw / no dedicated manifest yet. |
| **Geo / FIPS** | Hard — DMA/state native; county needs explicit crosswalk. |
| **Next free step** | Tiny keyword list + state-level monthly pilot; store under `data/raw/trends/` + add `google_trends.json`. |
| **Blockers** | Rate limits / DMA→county design. **No paid Trends API.** |

---

## G — Project ledger / denominators — **already-have-raw** (EIA) / **ready** for more free files

### EIA Form 861

| Field | Detail |
|-------|--------|
| **Free status** | **already-have-raw** |
| **Free access path** | Portal https://www.eia.gov/electricity/data/eia861/ · 2024 zip `https://www.eia.gov/electricity/data/eia861/zip/f8612024.zip` |
| **License / ToS** | US government work / public domain. |
| **Raw on disk** | **yes:** `data/raw/eia/f8612024.zip` (4,568,208 bytes; sha256 `77ce49c6…54de` per `eia_861_2024.json`) + extracted `Utility_Data_2024.xlsx` (260,483 bytes). |
| **Manifest** | `eia_861_2024.json` |
| **Geo / FIPS** | **`partial`.** Annual utility/territory — need utility→county FIPS; month grain is annual. |
| **Next free step** | Map service-territory fields onto Census county FIPS via `src/geo/fips.py`. |
| **Blockers** | None for access. |

**Live check (2026-09-16 PT):** portal **200**; 2024 zip **200**.

### LBNL Queued Up (current edition)

| Field | Detail |
|-------|--------|
| **Free status** | **ready** (URL verified; not downloaded) |
| **Free access path** | Portal https://emp.lbl.gov/queues · 2026 Edition https://emp.lbl.gov/publications/queued-2026-edition-characteristics · Excel: `https://emp.lbl.gov/sites/default/files/2026-05/LBNL_Ix_Queue_Data_File_thru2025.xlsx` (~15.6 MB). |
| **License / ToS** | **CC BY 4.0** — attribute LBNL and GridTracker. Generation/storage queues — **not** load / data-center permit registry. |
| **Raw on disk** | **no** — indexed in `project_ledger_sources.json` only. |
| **Geo / FIPS** | **`partial`** upstream (region/state/county map products); queue timestamps → `YYYY-MM` still need a transform plan. Do **not** invent proposed/approved/denied data-center counts. |
| **Next free step** | Download XLSX into `data/raw/lbnl/` + manifest `lbnl_queued_up_2026.json` (sha256, bytes, access date). |
| **Blockers** | None for free access. |

**Live check (2026-09-16 PT):** portal / publication / XLSX HEAD **200** (`content-length` 15571236).

### Major ISO / RTO open queue portals

Indexed in `project_ledger_sources.json`. Landing pages checked **200** on 2026-09-16 PT: PJM, MISO, CAISO, ERCOT, NYISO, ISO-NE, SPP. Schemas differ; **no national data-center permit registry exists** (spec failure mode G). Next: pick one ISO, document exact open CSV/XLSX URL + columns in a dedicated manifest before fetching.

### Opposition registries (hand-curated)

No free bulk national API. Public pointers (datacenterwatch.org etc.) are for hand curation — cite pages; prefer owned curated table with `county_fips` + `month`. **Zero fabricated rows.**

---

## D — News (notes; not free-backbone priority this phase)

| Source | Status | Blocker |
|--------|--------|---------|
| Media Cloud free research API | `documented_only` (`media_cloud.json`, `MC_API_KEY` absent) | Aden free account / key; weekly quota |
| Local RSS/HTML | policy only — no feed list yet | Legal/ToS per site; curate feeds first |
| NewsBank Access World News | **paid — excluded from free backbone** | Keep excluded |

---

## Geography crosswalk (Census) — **already-have-raw**

| Field | Detail |
|-------|--------|
| **Free access** | `https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_counties_national.zip` — public domain |
| **Raw on disk** | `data/raw/census/2024_Gaz_counties_national.txt` (647,830 bytes; sha256 `0a121d13…4451`; 3,222 counties + header) + zip (141,679 bytes) |
| **Manifest** | `census_gaz_counties_2024.json` |
| **Helper** | `src/geo/fips.py` |
| **FIPS × month** | **`ready`** for county universe / USPS↔GEOID joins (month not in gazetteer). |

---

## H — Calibration (as published)

Pew, Gallup, AP-NORC national AI/tech series and ballot measures: **cite release pages**; no automated free bulk assumed. Not part of free county×month backbone ingest this phase.

---

## Exact next free ingest actions (priority A→B→E)

1. **A:** `python -m src.ingest.localview --include-meta` (meta parquet only; no transcript tarballs).
2. **E:** Already past raw + `ccc_rules_v0` transform; optional phase-2 CCC backfill later.
3. **G:** Download LBNL Queued Up 2026 XLSX (URL above) + manifest.
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
| G1 | No national DC permit registry | Accept hand-built ledger coverage (spec failure mode G) |
| Ops | GitHub remote missing | Local `.git` only (`git remote` empty) — create private remote when ready; **do not push from this agent** |

---

## Git / dump policy

- Tracker `.gitignore` excludes large `data/raw/**` formats. Keep **manifests** in git; keep **dumps** on disk only.
- Prefer a **single** raw copy under this repo’s `data/raw/` (do not duplicate into free-data workspace).
- Free-data workspace at `/workspace/ai-backlash-free-data` is notes-only (no `.git`); do not `git init` it.

---

## Verification log

**Verified on disk 2026-09-16 PT (ls sizes + sha256sum where checked):** CCC CSV 47,231,658 bytes / sha256 matches manifest; LocalView codebook 6,387 / sha256 matches; EIA zip 4,568,208 / sha256 matches; Census txt 647,830 / sha256 matches; LegiScan/Open States/Arctic Shift raw empty or ACCESS-only; CCC processed events/panel/QA present as above.

**Verified live with curl 2026-09-16 PT:** LBNL Queued Up portal + 2026 XLSX; EIA; CCC; LocalView DOI/codebook/meta; LegiScan (**403**); Open States docs; Arctic Shift; Media Cloud; Census zip; major ISO landing pages; datacenterwatch.org.

**Reconciled from:** `SOURCES.md`, `data/manifests/*.json`, on-disk `data/raw/**` / `data/processed/**`, and draft inventory formerly at `/workspace/ai-backlash-free-data/docs/SOURCE_INVENTORY.md`.
