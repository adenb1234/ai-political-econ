-- AI Backlash Tracker — panel spine
-- One row per place × month. Counts by layer, denominators, derived shares.

CREATE TABLE IF NOT EXISTS panel (
    county_fips         TEXT NOT NULL,             -- 5-digit GEOID
    state               TEXT NOT NULL,             -- USPS 2-letter
    month               TEXT NOT NULL,             -- YYYY-MM
    -- numerator counts by layer (nullable until that layer is wired)
    n_deliberation      INTEGER,                   -- A
    n_legislation       INTEGER,                   -- B
    n_ordinances        INTEGER,                   -- C
    n_news              INTEGER,                   -- D
    n_mobilization      INTEGER,                   -- E
    n_vernacular        INTEGER,                   -- F
    n_project_actions   INTEGER,                   -- G: decisions / filings counted as events
    -- denominators (layer G and B especially)
    n_projects_proposed INTEGER,
    n_projects_approved INTEGER,
    n_projects_denied   INTEGER,
    n_projects_delayed  INTEGER,
    n_bills_introduced  INTEGER,
    n_bills_enacted     INTEGER,
    -- derived shares (store explicitly for citation stability; recompute on revision)
    share_opposed_of_proposed   REAL,
    share_delayed_of_proposed   REAL,
    share_blocked_of_proposed   REAL,
    share_enacted_of_introduced REAL,
    -- grievance mix (JSON object: taxonomy_id -> count or share)
    grievance_mix       TEXT,
    taxonomy_version    TEXT NOT NULL DEFAULT 'taxonomy_v0.1',
    as_of               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (county_fips, month),
    CHECK (county_fips ~ '^[0-9]{5}$'),
    CHECK (state ~ '^[A-Z]{2}$'),
    CHECK (month ~ '^[0-9]{4}-[0-9]{2}$')
);

CREATE INDEX IF NOT EXISTS idx_panel_state_month
    ON panel (state, month);
