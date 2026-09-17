# Senate LDA AI / data-center / semiconductor / utility filter — `lda_rules_v0`

**Version:** `lda_rules_v0`  
**Access / probe date:** 2026-09-16 (PT)  
**Source:** Senate LDA.gov REST API `GET /api/v1/filings/` (anonymous; no key)  
**Implemented in:** `src/ingest/senate_lda.py`  
**Policy:** precision over recall; **do not invent** filings or `county_fips`. Document query seeds separately from keyword hits.

## API query seeds (`client_name` partial match)

Live API supports `client_name` (and `registrant_name`) filtering. Third-party OpenAPI lists `issue_code`, but a **2026-09-16 PT probe** showed `issue_code` / `general_issue_code` **do not change result counts** vs year-only — v0 therefore **does not** use issue-code server filters.

Default seeds (comma-separated in code `CLIENT_NAME_SEEDS`):

| Seed | Intent |
|------|--------|
| OpenAI, Anthropic, xAI, NVIDIA, CoreWeave | AI / GPU / AI infra clients |
| data center, Equinix, Digital Realty, CyrusOne, Vantage Data | Data-center operators / phrasing |
| Semiconductor, Taiwan Semiconductor, Micron Technology, Advanced Micro Devices, GlobalFoundries | Semiconductor clients / associations |
| Edison Electric, American Electric Power, Duke Energy, Dominion Energy, Southern Company, NextEra Energy | Major electric utilities / trade |

Intersected with filing years **2023–2025** by default. Deduped by `filing_uuid`.

## Client-side keyword allowlist (case-insensitive)

Applied to joined text: client name + client description + registrant name/description + lobbying activity issue display + activity description.

| Term id | Pattern family |
|---------|----------------|
| data_center / datacenter | data center(s) / datacenter(s) |
| server_farm / hyperscale | synonyms |
| artificial_intelligence / agi / generative_ai | AI phrases |
| chatgpt / openai / anthropic / nvidia / coreweave | named orgs/products |
| machine_learning / llm / gpu / ai_word (`\bAI\b`) | tech terms |
| semiconductor / chipmaker | semiconductor / fab / foundry |
| electric_utility / power_utility | electric utility phrasing |
| data_center_operator | equinix / digital realty / cyrusone / vantage data |

## Explicit non-goals (v0)

- Inventing matches from bare Big-Tech names without an allowlist hit in the scanned fields.
- Using ineffective `issue_code` API filters as if they worked.
- Inventing `county_fips` — federal LDA is rarely county-grained; use `client.state` / `ppb_state` when USPS-2; leave county blank with QA note.
- Full historical dump of all LDA filings (rate limits + size); use bulk XML portal if needed later.

## Outputs

- Raw: `data/raw/senate_lda/filings_sample_v0.jsonl` (+ `fetch_meta_v0.json`, `ACCESS.md`) — gitignored bulk JSON
- Processed: `data/processed/lobbying/senate_lda_ai_related_v0.csv` + `.jsonl`
- QA: `data/processed/qa/senate_lda_ai_related_v0_qa.json`
- Manifest: `data/manifests/senate_lda.json`
