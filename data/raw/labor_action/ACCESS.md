# Cornell–Illinois Labor Action Tracker — access notes

**Layer:** E (mobilization) complement — strikes / labor protests (manual LAT methodology; not a complete protest census).  
**Access check:** 2026-09-16 (PT).

## Free public paths (no email / no login)

| Asset | URL | Notes |
|-------|-----|-------|
| Interactive map / site | https://striketracker.ilr.cornell.edu/ | GitHub Pages SPA |
| Live JSON deploy | https://striketracker.ilr.cornell.edu/labor_actions.json | Built from Grist → `labor_actions.json` by [ilrWebServices/StrikeSiteTracker](https://github.com/ilrWebServices/StrikeSiteTracker) Actions; **preferred free ingest** |
| Project page | https://www.ilr.cornell.edu/faculty-and-research/labor-action-tracker | Annual reports; methodology pointer |
| Methodology | https://striketracker.ilr.cornell.edu/methodology.html | Definitions / protocols |
| Zenodo snapshot | https://doi.org/10.5281/zenodo.16457619 | CC BY 4.0; files include `Labor-prod.xlsx` + sqlite dump (third-party packaging of LAT; cite LAT + Zenodo) |

Fetcher: `python -m src.ingest.labor_action_tracker` / `make fetch-labor-action`.

## Email-gated spreadsheet (blocked for automated free ingest)

Official project page: for a spreadsheet version, email Johnnie Kallas (`jkallas@illinois.edu`).  
We **do not** invent rows or scrape behind that gate. Manifest status for the email spreadsheet path: `documented_only` / access `blocked` without human email request. Prefer the public Pages JSON.

## Coverage honesty

- Strikes: LAT states relatively high confidence for comprehensive strike capture from ~2021 onward.  
- Labor protests: **not** a complete count — general understanding only.  
- Map pins are **locations** (one action at five sites → five map points).  
- Manual coding from public sources; not a substitute for CCC protest events or BLS large work-stoppage series alone.

## Citation

Kallas, J., Iyer, D. K., & Friedman, E. Labor Action Tracker. Cornell ILR & Illinois LER. https://striketracker.ilr.cornell.edu/
