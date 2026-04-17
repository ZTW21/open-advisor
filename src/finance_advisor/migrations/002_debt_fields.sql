-- Migration 002 — debt fields and allocation targets
--
-- Adds columns to support Phase 9 advisory flows:
--   accounts.apr            — annual percentage rate (for credit_card, loan, mortgage)
--   accounts.min_payment    — minimum monthly payment
--   accounts.asset_class    — for rebalance: 'cash' | 'us_stocks' | 'intl_stocks'
--                             | 'bonds' | 'real_estate' | 'liability' | 'other' | NULL
--
-- All new columns are NULLable. Existing rows need no backfill. Non-debt
-- accounts typically leave apr/min_payment NULL; non-investment accounts
-- typically leave asset_class NULL (the rebalance command has a sensible
-- default mapping by account_type when asset_class is unset).
--
-- Also introduces `allocation_targets`: the user's desired allocation by
-- asset class, versioned by `active_from`. Latest row per asset class wins.

ALTER TABLE accounts ADD COLUMN apr REAL;
ALTER TABLE accounts ADD COLUMN min_payment REAL;
ALTER TABLE accounts ADD COLUMN asset_class TEXT
    CHECK (asset_class IN (
        'cash', 'us_stocks', 'intl_stocks', 'bonds',
        'real_estate', 'liability', 'other'
    ));

CREATE TABLE IF NOT EXISTS allocation_targets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_class   TEXT NOT NULL
        CHECK (asset_class IN (
            'cash', 'us_stocks', 'intl_stocks', 'bonds',
            'real_estate', 'other'
        )),
    target_pct    REAL NOT NULL CHECK (target_pct >= 0 AND target_pct <= 100),
    active_from   TEXT NOT NULL,
    notes         TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (asset_class, active_from)
);

INSERT OR IGNORE INTO schema_version (version) VALUES (2);
