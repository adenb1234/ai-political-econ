# CCC AI / data-center keyword filter — `ccc_rules_v0`

**Version:** `ccc_rules_v0`  
**Classifier pin:** `taxonomy_v0.1+ccc_rules_v0`  
**Access date for this note:** 2026-09-16 (PT)  
**Source fields scanned:** `title`, `claims_summary`, `claims_verbatim`, `issue_tags_summary`, `issue_tags_verbatim`, `issues`, `organizations`, `targets`, `notes`  
**Policy:** precision over recall. Headline series must reproduce from these rules alone (no LLM).

Implemented in `src/transform/ccc_to_events.py` as `RULES` / `FILTER_VERSION`.

## Allowlist (case-insensitive)

| Term / pattern | Notes |
|----------------|-------|
| `data center` / `data centre` (optional space or hyphen) | Core infrastructure opposition |
| `datacenter` / `datacentre` | Compact spelling |
| `server farm` / `server farms` | Synonym |
| `hyperscale` | Hyperscale facility framing |
| `artificial intelligence` | Full phrase |
| `artificial general intelligence` / `AGI` | AGI / ASI protests |
| `artificial superintelligence` / `ASI` | |
| `generative AI` | |
| `\bAI\b` | Whole-word only (avoids matching inside longer tokens) |
| `ChatGPT` | Product |
| `OpenAI` | Firm |
| `machine learning` | |
| `\bLLM\b` / `\bLLMs\b` | |
| `\bGPU\b` / `\bGPUs\b` | Compute / chip framing |
| `automation` | Labor / displacement framing |
| `robot` / `robots` / `robotic` | Prefer precision; known slogan FP risk (see below) |
| `crypto mining` / `cryptocurrency mining` / `bitcoin mining` | **Only if** co-occurring with data-center / energy / electricity / power / hyperscale / AI terms in the same scanned blob |

## Explicit non-goals (v0)

- Generic tech protests without AI / data-center / automation language (e.g. “against Microsoft” alone, “against Palantir” alone) — retained **only** if an allowlist term also appears (e.g. “Palantir providing AI technology”).
- Broad climate / Gaza / labor events that mention “AI” only as a chant aside still match via `\bAI\b` — accepted as precision tradeoff for reproducibility; audit in QA samples.
- Paid news APIs or LLM classification — out of scope for this filter version.

## Known false-positive risks

| Pattern | Example risk | Mitigation in v0 |
|---------|--------------|------------------|
| `robot` / `robots` | Slogan titles like “I Am Not a Robot” (Amazon labor) | Drop if **only** robot-family hit and no other allowlist term |
| `\bAI\b` | Chants that name AI without AI being the primary grievance | Kept (reproducible); grievance map may still be empty |
| Crypto mining alone | Environmental crypto protests unrelated to AI load | Require co-occurrence with data-center / energy / AI terms |

## Stance assumption

CCC protest / demonstration / rally rows default to stance `oppose` (organized opposition capacity). CCC `valence` codes `0/1/2` are recorded in QA only — no silent remapping without a published codebook mapping.

## Referent heuristic (not part of the allowlist)

- **local** if claims/title mention local siting language (data center + rezoning / proposed / county / city project names, etc.)
- **national** if national/federal / industry-wide AI policy / major labs (OpenAI, ChatGPT, AGI) without local siting
- else **ambiguous**

## Grievance map (keyword → `taxonomy_v0.1`)

Small explicit map in code (`GRIEVANCE_KEYWORDS`). Empty list if nothing matches. Multi-label allowed; first match order follows taxonomy table order in code.

## Outputs

- `data/processed/events/ccc_ai_related_v0.jsonl`
- `data/processed/events/ccc_ai_related_v0.csv`
- `data/processed/panel/ccc_mobilization_counts_v0.csv`
- `data/processed/qa/ccc_ai_related_v0_qa.json`

## How to bump the version

1. Copy this file to `ccc_ai_keywords_vN.md` and edit terms.
2. Update `FILTER_VERSION` / `CLASSIFIER_VERSION` in `ccc_to_events.py`.
3. Re-run `make transform-ccc` and archive prior processed filenames (do not overwrite without a version bump).
