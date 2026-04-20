-- Persistent advisor insights — observations a financial advisor would share.
-- Migration 005.

CREATE TABLE IF NOT EXISTS insights (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_key  TEXT NOT NULL UNIQUE,
    type         TEXT NOT NULL,
    severity     TEXT NOT NULL CHECK (severity IN ('positive', 'info', 'warn', 'alert')),
    title        TEXT NOT NULL,
    body         TEXT NOT NULL,
    source       TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
    dismissed_at TEXT,
    is_current   INTEGER NOT NULL DEFAULT 1
);

INSERT OR IGNORE INTO schema_version (version) VALUES (5);
