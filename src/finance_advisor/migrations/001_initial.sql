-- Initial schema for finance-advisor.
-- Migration 001 — creates all core tables.
-- Idempotent: uses IF NOT EXISTS everywhere so rerunning is safe.

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Accounts
CREATE TABLE IF NOT EXISTS accounts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    institution   TEXT,
    account_type  TEXT NOT NULL CHECK (account_type IN (
        'checking', 'savings', 'credit_card', 'brokerage',
        'retirement', 'loan', 'mortgage', 'cash', 'other'
    )),
    currency      TEXT NOT NULL DEFAULT 'USD',
    active        INTEGER NOT NULL DEFAULT 1,
    opened_on     TEXT,
    closed_on     TEXT,
    notes         TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Balance history (one row per account per as-of date)
CREATE TABLE IF NOT EXISTS balance_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id   INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    as_of_date   TEXT NOT NULL,
    balance      REAL NOT NULL,
    source       TEXT CHECK (source IN ('manual', 'import', 'reconcile', NULL)),
    notes        TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(account_id, as_of_date)
);
CREATE INDEX IF NOT EXISTS idx_balance_history_date
    ON balance_history(as_of_date);

-- Categories (hierarchical)
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    parent_id   INTEGER REFERENCES categories(id),
    is_transfer INTEGER NOT NULL DEFAULT 0,
    is_income   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Imports (audit log of statement imports)
CREATE TABLE IF NOT EXISTS imports (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file    TEXT NOT NULL,
    file_checksum  TEXT NOT NULL,
    imported_at    TEXT NOT NULL DEFAULT (datetime('now')),
    row_count      INTEGER NOT NULL DEFAULT 0,
    new_count      INTEGER NOT NULL DEFAULT 0,
    dup_count      INTEGER NOT NULL DEFAULT 0,
    flagged_count  INTEGER NOT NULL DEFAULT 0,
    status         TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'committed', 'rolled_back', 'failed'))
);

-- Transactions
-- amount: positive = inflow to the account, negative = outflow
-- dedup_key: sha256(account_id|iso_date|amount|normalized_description)
CREATE TABLE IF NOT EXISTS transactions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id            INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    date                  TEXT NOT NULL,
    amount                REAL NOT NULL,
    merchant_normalized   TEXT,
    description_raw       TEXT NOT NULL,
    category_id           INTEGER REFERENCES categories(id),
    notes                 TEXT,
    pending               INTEGER NOT NULL DEFAULT 0,
    transfer_group_id     TEXT,
    import_batch_id       INTEGER REFERENCES imports(id),
    dedup_key             TEXT NOT NULL UNIQUE,
    created_at            TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_transactions_date
    ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_account_date
    ON transactions(account_id, date);
CREATE INDEX IF NOT EXISTS idx_transactions_category
    ON transactions(category_id);
CREATE INDEX IF NOT EXISTS idx_transactions_import_batch
    ON transactions(import_batch_id);

-- Holdings (investment positions)
CREATE TABLE IF NOT EXISTS holdings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id   INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    ticker       TEXT NOT NULL,
    shares       REAL NOT NULL,
    cost_basis   REAL,
    as_of_date   TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(account_id, ticker, as_of_date)
);

-- Categorization rules (applied during import)
CREATE TABLE IF NOT EXISTS categorization_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    match_pattern   TEXT NOT NULL,
    match_type      TEXT NOT NULL DEFAULT 'substring'
        CHECK (match_type IN ('substring', 'regex', 'exact')),
    category_id     INTEGER NOT NULL REFERENCES categories(id),
    account_filter  TEXT,
    amount_filter   TEXT,
    priority        INTEGER NOT NULL DEFAULT 100,
    user_defined    INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_categorization_rules_priority
    ON categorization_rules(priority DESC);

-- Budget plan (one row per category per active window)
CREATE TABLE IF NOT EXISTS budget_plan (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id   INTEGER NOT NULL REFERENCES categories(id),
    amount        REAL NOT NULL,
    active_from   TEXT NOT NULL,
    active_to     TEXT,
    notes         TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Goals
CREATE TABLE IF NOT EXISTS goals (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    target_amount  REAL,
    target_date    TEXT,
    priority       INTEGER NOT NULL DEFAULT 5,
    status         TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'paused', 'completed', 'abandoned')),
    notes          TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS goals_progress (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id      INTEGER NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    as_of_date   TEXT NOT NULL,
    amount       REAL NOT NULL,
    notes        TEXT,
    UNIQUE(goal_id, as_of_date)
);

-- Recurring transactions (detected subscriptions, salary, etc.)
CREATE TABLE IF NOT EXISTS recurring (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern         TEXT NOT NULL,
    account_id      INTEGER REFERENCES accounts(id),
    typical_amount  REAL,
    frequency       TEXT CHECK (frequency IN
        ('daily', 'weekly', 'biweekly', 'monthly', 'quarterly', 'yearly', NULL)),
    last_seen       TEXT,
    status          TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'paused', 'cancelled', 'review'))
);

-- Record that migration 001 has been applied
INSERT OR IGNORE INTO schema_version (version) VALUES (1);
