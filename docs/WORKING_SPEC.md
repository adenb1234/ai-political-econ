# AI Backlash Tracker — Working Spec

**Status:** draft for internal discussion
**Owner:** Economics team

---

## The bet

The constraint in this debate is not opinion data. Public disapproval of AI is already high and already well measured. The constraint is that every number in circulation is a *numerator* — projects blocked, groups formed, bills introduced, protests held — scattered across a dozen incompatible sources, with no denominators, no consistent geography, and no fixed release cadence.

Whoever collates that becomes the reference source. That is the whole thesis. The plumbing is the moat, not the estimator.

**What this is:** one place where scattered evidence of organized AI opposition in the US is pulled into a common schema, keyed to common geography and time, published on a fixed cadence, with inputs open.

**What this is not:** a sentiment map, a forecast, or a single headline number. Those are downstream options, not the product.

---

## Principles

- **Collate before modeling.** Ship the assembled data before any clever estimator.
- **Every count gets a denominator.** A count of blocked projects without a count of proposed projects is not a measurement.
- **Two geography keys (county FIPS, state), one time key (month).** If a source can't be crosswalked to those, it doesn't ship.
- **Reproducible backbone, model-assisted enrichment.** Keyword and structured rules define any headline series so it reproduces in five years. LLM classification adds grievance category and stance on top, versioned and prompt-published.
- **Publish inputs, not just outputs.** The dataset is the citation magnet, not the analysis.

---

## Data layers

| | Layer | What it captures | Source and access | Refresh | Build |
|---|---|---|---|---|---|
| A | Deliberation | What local officials and residents say in formal settings | LocalView transcripts (free, auto-updating). Granicus / Legistar / Swagit scrapers later if coverage gaps matter | Monthly | ~1 wk |
| B | Legislation | What gets introduced, sponsored, voted, enacted | LegiScan bulk datasets — all 50 states + Congress, bills, sponsors, roll calls, full text. Free tier. Open States v3 for committee detail | Weekly | ~3 d |
| C | Ordinances & moratoria | Binding local action, and template diffusion across jurisdictions | Local ordinance text; partly detectable via similarity to known model ordinances | Quarterly | Ongoing manual |
| D | News | Salience and framing at local scale | NewsBank Access World News (~3,500 local papers — the corpus BBD used for state-level EPU). Media Cloud as free complement | Monthly | ~2 wk + access |
| E | Mobilization | Organized opposition capacity | Crowd Counting Consortium (all states, since 2017, near-daily). Hand-curated opposition group registry. Data Center Watch as cross-reference | Monthly | ~1 d + curation |
| F | Vernacular | Unprompted local sentiment | Reddit — Arctic Shift for backfill, official API for ongoing. Google Trends at DMA level | Monthly | ~1 wk + crosswalk |
| G | Project ledger | The denominator layer | Proposed / approved / denied / delayed data centers; interconnection queues (LBNL, ISO); utility rate cases (EIA-861, state PUC dockets) | Quarterly | ~2 wk |
| H | Calibration | Ground truth for everything above | Pew, Gallup, AP-NORC national series; ballot measure results | As published | ~2 d |

### Known biases, stated up front rather than discovered by a referee

- **A:** places that record meetings skew larger, richer, more urban. Public commenters are unrepresentative of residents — this measures expressed opposition among the activated, not public opinion.
- **B:** introduced ≠ enacted. Sponsor district ≠ constituent opinion. LegiScan person records reflect *current* district and party, so historical attribution needs the person_hash check.
- **D:** news deserts correlate with rural and economically exposed places. The coverage gap is not random and runs against the places that matter most.
- **F:** posters in a city subreddit are not a sample of that city. Trends measures salience only, and returns relative indices — series are incomparable across pulls without a constant anchor term.
- **G:** no national permit registry exists. Coverage is whatever we build.

---

## The spine

Two tables. Everything else is a view.

**`events`** — one row per discrete thing that happened: a bill, a meeting mention, a protest, a permit decision, an ordinance.

> `event_id · county_fips · state · cbsa · date · layer · source_url · grievance · stance · referent (local/national) · confidence · classifier_version`

**`panel`** — one row per place × month: counts by layer, denominators, derived shares.

### Grievance taxonomy

This is the actual intellectual product. Everything else is plumbing.

energy & grid cost · water · land use, noise, aesthetics · tax abatement & fiscal · jobs & displacement · schools & education · safety & control · data & privacy · creative work & IP

Every layer gets tagged into the same taxonomy. That is what makes collation worth anything — it's the only way to say "opposition in Ohio is about electricity bills and opposition in California is about jobs" and have the claim mean something.

**Freeze the taxonomy at the end of phase 1.** Version any later change and republish affected history. Taxonomy churn is the quiet way a project like this loses comparability.

---

## Outputs, ordered by who would actually cite them

1. **Conversion funnel.** Of proposed data centers, what share draws organized opposition, what share is delayed, what share is blocked. Of introduced AI bills, what share is enacted. Nobody has published this. Every position in the current debate depends on an implicit conversion rate that no one has been forced to state.
2. **Quarterly release.** Short written brief, revised numbers, changelog. The cadence is the product as much as the data.
3. **State fact sheets.** One page each — what's pending, what's organized, what the grievance mix is. Cheapest thing to produce, most useful to a legislative staffer or agency contact.
4. **Opposition capacity scorecard.** Groups, legislators on record, template availability. Forward-looking, which is what makes it citable.
5. **Public dataset + data descriptor paper.** The LocalView move: low novelty bar, high citation yield, every downstream user becomes distribution. Outside co-author.
6. **Backlash index.** Local-referent and national-referent series, EPU-style. Optional. Least important thing on this list and the most tempting to start with.
7. **Map.** Last, if ever. A figure inside output 1, not a product.

---

## Build phases

1. **Weeks 1–2.** Schema, geography crosswalk, grievance taxonomy, hand-labeled gold set. No ingest.
2. **Weeks 3–6.** Layers A, B, E. First internal numbers. Decide whether variance is real before building anything else.
3. **Weeks 7–12.** Layer G, then D pending NewsBank access. First external release: funnel + state fact sheets.
4. **Months 4–6.** Layers C, F. Dataset release with external co-author.
5. **Ongoing.** Quarterly cadence, revisions, index only if warranted.

---

## Staffing and cost

- 0.5 FTE data engineer, ongoing — mostly absorbing upstream schema changes, not new code
- 1 RA — hand validation, opposition group registry, ordinance curation. The unautomatable parts are what make it credible
- 1 researcher owning the brief and the taxonomy
- Main cash line: NewsBank institutional access. Settle this early, since it gates layer D entirely

---

## Credibility

Mercor publishing an AI backlash tracker invites an immediate question about whose interest it serves, and that question can sink the output regardless of measurement quality. Yale's climate opinion maps don't have this problem because Yale isn't selling anything.

Three mitigations, all committed **before** the first release rather than added after someone raises the objection:

- External co-authorship on the dataset paper
- Methodology posted before results exist, and not revised once they do
- Disconfirming findings led with, not buried. If backlash turns out milder than the discourse assumes, that's the headline

---

## Failure modes

- **Drifting into a sentiment map.** Sentiment is ambient and close to maxed out. Capacity and conversion are the missing quantities.
- **Numerators without denominators.** That's Data Center Watch with more steps.
- **Missing a release.** Two misses and the project is dead regardless of data quality.
- **Model version drift** silently breaking series continuity. Pin versions, keep the gold set frozen, publish prompts.
- **Scope creep into causal work too early.** One clean paper belongs downstream of the infrastructure, not as its justification.
