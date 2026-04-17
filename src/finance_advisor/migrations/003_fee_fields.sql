-- Migration 003 — fee audit fields
--
-- Adds columns for the quarterly fee audit (Phase 10):
--   accounts.expense_ratio_pct — weighted-average expense ratio, as a percentage
--                                (e.g., 0.03 for a 0.03% index fund blend).
--                                Stored per-account because we don't track
--                                individual fund holdings yet.
--   accounts.annual_fee        — flat annual fee in account currency
--                                (e.g., a $75 AMEX Platinum card, a $25
--                                brokerage inactivity fee).
--
-- Both NULL by default. `finance fees` reports only accounts with at least
-- one of these populated, so unfilled rows are silently skipped.
--
-- No backfill — users can edit `finance account edit <name> --expense-ratio X
-- --annual-fee Y` when they learn the values.

ALTER TABLE accounts ADD COLUMN expense_ratio_pct REAL;
ALTER TABLE accounts ADD COLUMN annual_fee REAL;

INSERT OR IGNORE INTO schema_version (version) VALUES (3);
