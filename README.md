# AI Political Economy / Backlash Tracker

**Repo:** [adenb1234/ai-political-econ](https://github.com/adenb1234/ai-political-econ) (private)  
**Status:** free-data backbone in progress · schema freeze `taxonomy_v0.1`  
**Not this:** a national sentiment heat map, a single “AI hate index,” or a paid-API product

## What this is for

Scattered *numerators* (protests, bills, moratoria, meeting fights) dominate the AI-backlash conversation. Almost nobody publishes them with **denominators**, **shared geography**, and a **fixed cadence**.

This project builds a **county × month** evidence spine for organized US AI / data-center political economy:

| People should be able to see… | Example exhibit |
|---|---|
| Where formal local conflict shows up | Meetings, ordinances, moratoria by county-month |
| Where statutes move | AI / data-center bills introduced → enacted |
| Where people organize in public | Protests, groups, ballot fights |
| How loud the local press is | Story counts / framing (free Media Cloud first) |
| What share of *proposed* load faces friction | Opposition ÷ projects / MW at risk |
| What the fight is *about* | Shared grievance tags (power, water, fiscal, land, labor, privacy…) |

**Spine keys:** `county_fips` (5-digit) · `state` (USPS) · `month` (`YYYY-MM`).  
Two tables: `events` (one discrete thing) and `panel` (place × month). Details: [`docs/WORKING_SPEC.md`](docs/WORKING_SPEC.md), [`docs/TAXONOMY.md`](docs/TAXONOMY.md).

---

## Priority order (build sequence)

Freeze priority for free work: **A → B → E → G → C(inventories) → F → D(thin) → H**.  
Paid NewsBank / heavy LLM labeling sit **after** a live free demo (BlueDot ~$1.5k ask is for labeling the free spine, not NewsBank).

| Priority | Layer | Role in the product |
|---:|---|---|
| 1 | **A** Deliberation | Earliest *formal* local signal (meetings) |
| 2 | **B** Legislation | Statewide rule-making & preemption |
| 3 | **E** Mobilization | Street / campaign capacity |
| 4 | **G** Project ledger | **Denominators** (without this, every rate is fake) |
| 5 | **C** Ordinances & moratoria | Binding local pauses / bans (high value; partly covered by open third-party inventories) |
| 6 | **F** Vernacular | Unprompted talk (Reddit / Trends) — noisy, still useful for salience |
| 7 | **D** News | Local salience / framing (Media Cloud free → NewsBank only if funded) |
| 8 | **H** Calibration | Surveys / ballots that keep us honest |

---

## Data sources → what they exhibit

Scan date: **2026-09-16 PT**. Honest about free vs key vs paid, and what’s on disk in this repo. Fresh pass covered academic dumps, open trackers, grid/water/PUC sources, ballot measures, and news APIs — not only the original A–H list.

### Core layers (A–H)

| ID | Source | What it exhibits (the “so what”) | Access | On disk now? |
|---|---|---|---|---|
| **A1** | **LocalView** meeting meta (+ optional transcripts) — Harvard Dataverse | Places where AI / data-center / power / water fights enter *official* local agendas and public comment | Free (transcripts multi-GB; deferred) | **Yes** — codebook + meta; place→county crosswalk v0; meta spine v0 (~83% spine-ready) |
| **B1** | **LegiScan** bulk / free API | Introduction, sponsors, text, votes for state + federal AI / DC / energy bills → conversion funnel | Free account / key (bulk portal login-gated from this box) | **Blocked** — needs Aden free ZIP or `LEGISCAN_API_KEY` |
| **B2** | **Open States** | Committee detail beyond LegiScan | Free key | Documented only |
| **B3** | **NCSL AI Legislation Database** + **Zenodo US State AI Legislation Corpus** (~2.5k bills 2019–2026) | Curated / classified AI bill universe for validation against LegiScan pulls | Free browse / Zenodo dump | Not ingested yet (strong B complement) |
| **B4** | **CAID / DU State AI Policy Tracker** | Live state AI bill dashboard cross-walked to NCSL | Free web; bulk via Plural heritage | Not ingested |
| **C1** | **Moratorium Nation** (`mjbommar/moratorium-data-2026`) | Local *pauses* on data centers / related infra (jurisdiction, status, dates, legal fields) | Free GitHub CSV/JSON | **Not yet** — high-priority add for layer C |
| **C2** | **AI GridWatch** open data (moratoria + community actions, projects, facilities, state profiles) | Broader “pushback actions,” project outcomes, facility registry — CC BY 4.0 downloads | Free CSV/JSON | **Not yet** — high-priority add |
| **C3** | Hand / Legistar–Granicus scrapers | Ordinance text & template diffusion when inventories miss a town | Sweat / ToS-limited | Not started |
| **D1** | **Media Cloud** | Local/national story volume & source sets on AI / data centers (thin free news layer) | Free research key + weekly quota | Documented; needs `MC_API_KEY` |
| **D2** | Local RSS / HTML + GridWatch story archive | Headline chronologies without NewsBank | Free / messy | Partial (external) |
| **D3** | **NewsBank Access World News** | Dense local-paper corpus (BBD-style) | **Paid / institutional (~mid 4–5 figures/yr)** | **Excluded** from free backbone |
| **E1** | **Crowd Counting Consortium (CCC)** phase 2/3 | Protest / rally events; filter to AI / data-center / grid claims | Free Dataverse | **Yes** — phase 3 raw + AI-related events/panel v0 |
| **E2** | Opposition group registries (e.g. Data Center Opposition report FB census; Humans First action lists) | Organized *capacity*, not just event counts | Mostly manual / report-derived | Not structured here yet |
| **F1** | **Arctic Shift** Reddit dumps | Unprompted local talk in city/topic subs (backfill) | Free torrents (large) | Documented only — no dump pulled |
| **F2** | Reddit official API | Ongoing vernacular after dumps | Free OAuth (rate limits) | Not wired |
| **F3** | Google Trends (state×month pilot) | Relative salience, not absolute opinion | Free `pytrends`; polite backoff; **no paid API** | **Pilot landed** (real series; intermittent 429); `county_fips` blank; DMA→county deferred |
| **G1** | **EIA-861** | Utility sales / territory context for rate & load fights | Public domain | **Yes** — raw zip |
| **G2** | **LBNL Queued Up** interconnection workbook | Generation/storage *supply* queues (context — **not** load/DC permits) | Free CC BY | **Yes** — 2026 XLSX; transforms thin |
| **G3** | ISO/RTO + utility **load** interconnection / large-load tariffs; FERC large-load dockets | True demand-side denominator where published | Patchwork public dockets | Documented; hand work |
| **G4** | Facility / project inventories (GridWatch projects, ATLAS / open DC maps, operator disclosures) | Proposed / operating sites to pair with opposition | Mixed free | Not merged |
| **G5** | **USGS** county water-use / thermoelectric reanalysis | Water-stress context (not DC-specific withdrawals) | Free | Not ingested |
| **G6** | **RateBase** / state PUC dockets | Rate cases & large-load tariff fights (who pays) | Some open datasets; else docket scraping | Not started |
| **H1** | Pew / Gallup / AP-NORC / Reuters–Ipsos | National attitude baselines so local spikes aren’t over-read | Usually free summaries; microdata varies | Notes only |
| **H2** | **Ballotpedia** data-center ballot measures; state/local election returns | Revealed preference when voters face AI/DC questions | Free pages; manual harvest | Not ingested |

### Additional free / near-free candidates (expanded scan 2026-09-16/17)

Ingest after A/B/E/G spine work — **none on disk yet** unless noted. Prefer native free portals; skip freemium PUC wrappers.

| Source | What it exhibits | Access |
|---|---|---|
| **Moratorium Nation** + **AI GridWatch** open CSVs | Local/state DC (and related) pauses, pushback, project outcomes | Free GitHub / CC BY 4.0 — **next C ingest** |
| **Legistar Web API** / Granicus / CivicPlus | Matters, ordinances, attachments where LocalView is thin | Free per client; rate politely |
| **Municode / eCode360 / clerk PDFs** | Codified zoning (permanent rules, not pauses) | Free browse; bulk often ToS-grey |
| **OpenPUC scrapers** + **OpenMPSC** + native PUC portals | Rate cases, large-load tariffs, intervenor fights | Free OSS / no-auth MI API / state HTML-PDF |
| **EPA EIS DB** (+ EDGI scraper); **BLM NEPA register** | NEPA friction (land/water/noise) for large projects | Free |
| **USGS NWIS / water-use**; state eWRIMS-style rights DBs | Hydro context vs legal water rights (keep distinct) | Free / heterogeneous state portals |
| **FERC eLibrary** | Transmission / large-load rate proceedings | Free browse; awkward bulk |
| **Cornell–ILR Labor Action Tracker**; **BLS Work Stoppages** | Strikes / labor protests (filter AI/tech/warehouse); coarse large stoppages | Free Zenodo / USG XLSX |
| **Ballotpedia** AI ed guidance + ballot-measure topics; **MEDSL / SOS returns** | School AI policy stance; revealed preference on AI/DC measures | Free web / academic |
| **Senate LDA.gov API/XML**; OpenSecrets (edu license); state lobby DBs; FEC bulk | Lobbying & money pressure on AI / DC / utilities | Free (OpenSecrets: account + attribution) |
| **CourtListener / RECAP** | Lawsuits opposing DCs/AI (stay off paid PACER) | Free mirror |
| **Common Crawl CC-NEWS**; **GDELT 2.0**; curated local RSS | Salience/framing at scale when Media Cloud quota binds | Free; heavy ops |
| **ACS / BLS QCEW**; city open zoning/parcel portals | Socioeconomic + siting controls for the panel | Free |
| **LocalView school-board slice** | School-board AI fights inside existing meta | Meta already on disk |

### Geo helpers (required plumbing)

| Source | Exhibits | Status |
|---|---|---|
| Census Gazetteer counties / places; place-by-county 2020; CT town→planning region | Place → `county_fips` for LocalView & others | **On disk**; powers crosswalk v0 |

---

## What a v0 public panel should show (target exhibits)

Once A+E+G(+C inventories) join cleanly:

1. **County-month event counts** by layer (meetings · protests · bills touching the county’s state · moratoria)  
2. **Grievance mix** (taxonomy tags) — power/grid cost, water, land/aesthetics, tax abatement, jobs, schools, safety/control, privacy, IP  
3. **Funnel sketch** — projects or MW mentioned vs delayed/blocked/opposed (only where denominators exist; never fake them)  
4. **State fact sheets** — pending bills, active moratoria, recent mobilizations  

If we cannot support an exhibit with a documented source row, we **don’t ship the number**.

---

## What’s actually done vs open (free only)

**In good shape locally + on `main`:** LocalView meta geo spine (A), CCC AI-related v0 (E), EIA + LBNL raw (G), Census geo helpers.  
**Blocked on Aden (still free):** LegiScan bulk ZIP or free API key (B).  
**Not pulled yet (free but high leverage):** Moratorium Nation + AI GridWatch inventories (**C** — next free wins), Media Cloud key (D thin), Arctic Shift dumps (F, heavy).  
**Paid / later:** NewsBank; dense LLM transcript labeling beyond BlueDot ~$1.5k pilot.

Operational matrix: [`docs/SOURCE_INVENTORY.md`](docs/SOURCE_INVENTORY.md) · URL notes: [`docs/SOURCES.md`](docs/SOURCES.md).

---

## Free-source policy

1. No paid API required for the backbone. NewsBank is optional D enrichment only.  
2. Prefer bulk / dump downloads over rate-limited APIs.  
3. Every shipped series crosswalks to county FIPS + state + month.  
4. Manifests under `data/manifests/` record URL, license, bytes, blockers — **no invented empirical rows**.  
5. Pin classifier / prompt versions when LLM enrichment is added.

---

## Repo layout

```
ai-political-econ/
├── README.md                 ← you are here (source → exhibit map)
├── docs/                     WORKING_SPEC, SOURCES, SOURCE_INVENTORY, TAXONOMY
├── schema/                   events.sql, panel.sql
├── src/                      ingest, geo, transform
├── data/raw/                 bulk inputs (large files gitignored)
├── data/manifests/           source metadata
├── data/processed/           crosswalks, spines, QA JSON
├── Makefile
└── pyproject.toml
```

## How to run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make fetch-all          # free pulls that need no credentials
python -m src.geo.fips --summary
```

---

## Funding note (short)

BlueDot Rapid ask locked at **~$1.5k**: ~$900 cheap/mid LLM labeling of LocalView meta + gold QA, ~$400 compute/storage, ~$200 contingency. Next raise (Manifund / TAIF) only after free demo exists — denser labeling + optional NewsBank, not more scaffold.

---

## License / attribution

Upstream data stay under their licenses (Census / EIA public domain; CCC & LocalView via Harvard Dataverse; LBNL CC BY; GridWatch CC BY 4.0; etc.). Cite sources on every public derivative.
