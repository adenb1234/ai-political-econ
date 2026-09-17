# Labor Action Tracker AI / data-center keyword filter — `lat_rules_v0`

**Version:** `lat_rules_v0`  
**Classifier pin:** `taxonomy_v0.1+lat_rules_v0`  
**Access date:** 2026-09-16 (PT)  
**Source:** Cornell–Illinois Labor Action Tracker Pages JSON (`data/raw/labor_action/labor_actions.json`)  
**Fields scanned:** `Employer`, `Labor_Organization`, `Local`, `Notes`, `Industry` (joined), `Worker_demands` (joined). **Not** `sources` URLs (path/query FP risk).  
**Policy:** precision over recall; allowlist family aligned with `ccc_rules_v0`. Do not invent matches.

Implemented in `src/transform/labor_action_to_events.py`.

## Allowlist (case-insensitive)

| Term / pattern | Notes |
|----------------|-------|
| `data center` / `data centre` | Core infrastructure |
| `datacenter` / `datacentre` | Compact spelling |
| `server farm(s)` | Synonym |
| `hyperscale` | Facility framing |
| `artificial intelligence` | Full phrase |
| AGI / ASI phrases | |
| `generative AI` | |
| `\bAI\b` | Whole-word |
| ChatGPT / OpenAI | Product / firm |
| `machine learning` / `\bLLM(s)?\b` / `\bGPU(s)?\b` | |
| `automation` / `robot(s|ic)` | Robot-only hits dropped |
| crypto/bitcoin mining | Only with energy/AI/data-center co-occurrence |

## Explicit non-goals (v0)

- Generic tech employer names alone (Amazon, Google, Microsoft) without an allowlist term.
- Treating LAT as a complete labor-protest census (it is not).
- Inventing `county_fips` — locations expose City/State/Zip/lat/lon only.

## Outputs

- `data/processed/events/lat_ai_related_v0.csv` + `.jsonl`
- `data/processed/panel/lat_mobilization_counts_v0.csv` (header-only until FIPS crosswalk)
- `data/processed/qa/lat_ai_related_v0_qa.json`
