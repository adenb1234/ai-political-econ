-- AI Backlash Tracker — events spine
-- One row per discrete thing that happened.
-- Geography keys: county_fips (5-digit), state (USPS). Time: date (day) + month derived.

CREATE TABLE IF NOT EXISTS events (
    event_id            TEXT PRIMARY KEY,          -- stable hash or source-native id prefixed by layer
    county_fips         TEXT,                      -- 5-digit GEOID; NULL only with QA exception
    state               TEXT NOT NULL,             -- USPS 2-letter
    cbsa                TEXT,                      -- optional CBSA code
    event_date          DATE NOT NULL,             -- calendar date of the event
    event_month         TEXT NOT NULL,             -- YYYY-MM, derived from event_date
    layer               TEXT NOT NULL,             -- A|B|C|D|E|F|G|H
    source              TEXT NOT NULL,             -- e.g. ccc, legiscan, localview
    source_url          TEXT,
    source_record_id    TEXT,                      -- upstream id
    grievance           TEXT,                      -- JSON array of taxonomy ids, primary first
    stance              TEXT,                      -- oppose|support|mixed|neutral_descriptive|unclear
    referent            TEXT,                      -- local|national|ambiguous
    confidence          REAL,                      -- 0-1 classifier / coder confidence
    classifier_version  TEXT,                      -- e.g. taxonomy_v0.1+rules_v0 or llm prompt pin
    title               TEXT,
    summary             TEXT,
    raw_payload_path    TEXT,                      -- path under data/raw or processed
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (layer IN ('A','B','C','D','E','F','G','H')),
    CHECK (state ~ '^[A-Z]{2}$'),
    CHECK (county_fips IS NULL OR county_fips ~ '^[0-9]{5}$'),
    CHECK (event_month ~ '^[0-9]{4}-[0-9]{2}$')
);

CREATE INDEX IF NOT EXISTS idx_events_geo_month
    ON events (county_fips, event_month);

CREATE INDEX IF NOT EXISTS idx_events_layer_month
    ON events (layer, event_month);

CREATE INDEX IF NOT EXISTS idx_events_state_month
    ON events (state, event_month);
