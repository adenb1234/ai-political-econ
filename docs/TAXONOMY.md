# Grievance taxonomy

**Status:** draft for phase 1 (freeze at end of phase 1; version any later change)  
**Role:** the intellectual product — every layer tags into the same categories so geographic comparisons mean something.

Version string for classifiers / gold sets: `taxonomy_v0.1`

## Categories

| ID | Label | Working definition (opposition framing) |
|----|-------|----------------------------------------|
| `energy_grid_cost` | Energy & grid cost | Electricity rates, capacity charges, grid upgrades, reliability risk attributed to AI / data-center load |
| `water` | Water | Water consumption, wastewater, aquifer stress for cooling or construction |
| `land_use_noise_aesthetics` | Land use, noise, aesthetics | Zoning, siting, light/noise pollution, visual impact, farmland conversion |
| `tax_abatement_fiscal` | Tax abatement & fiscal | PILOTs, abatements, local fiscal incidence, opportunity cost of incentives |
| `jobs_displacement` | Jobs & displacement | Job quality/quantity claims, automation displacement, construction vs permanent employment |
| `schools_education` | Schools & education | School funding, enrollment pressure, student data / ed-tech concerns tied to AI policy |
| `safety_control` | Safety & control | Physical safety, catastrophic risk, democratic / regulatory control of AI systems |
| `data_privacy` | Data & privacy | Surveillance, training-data consent, resident / worker privacy |
| `creative_work_ip` | Creative work & IP | Copyright, likeness, training on creative works, creator compensation |

## Stance (orthogonal to grievance)

| ID | Meaning |
|----|---------|
| `oppose` | Clear opposition to the referent project / bill / practice |
| `support` | Clear support |
| `mixed` | Explicitly mixed or conditional |
| `neutral_descriptive` | Mentions without stance |
| `unclear` | Insufficient text |

## Referent

| ID | Meaning |
|----|---------|
| `local` | Specific local project, ordinance, utility, or employer |
| `national` | National / industry-wide AI or federal policy |
| `ambiguous` | Cannot tell |

## Tagging rules (phase 1)

1. **Multi-label grievances allowed**; store as ordered list, primary grievance first.
2. Keyword / structured rules define any **headline** series so it reproduces in five years.
3. LLM classification may add grievance + stance on top; pin `classifier_version` and publish prompts.
4. Freeze this list before first external release. Taxonomy churn breaks comparability — version and republish affected history if changed.
5. Do not map an event into the panel until it has `county_fips` (or an explicit state-only exception logged in QA).

## Gold set

Hand-labeled gold set is phase-1 deliverable (not in this scaffold). Keep frozen once used for calibration.
