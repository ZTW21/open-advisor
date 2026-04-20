-- Per-account sign convention.
--
-- Some card issuers (Apple Card, BILT) export statements where purchases are
-- positive and payments/credits are negative — the opposite of the system's
-- standard convention (positive = inflow, negative = outflow).
--
-- The importer uses this column to flip signs at import time so the DB always
-- stores amounts in standard convention.
--
-- Values:
--   'standard'        — positive = inflow, negative = outflow (Chase, Ally, most banks)
--   'credit_positive' — positive = purchase/outflow (Apple Card, BILT)

ALTER TABLE accounts ADD COLUMN sign_convention TEXT NOT NULL DEFAULT 'standard'
    CHECK (sign_convention IN ('standard', 'credit_positive'));

UPDATE accounts SET sign_convention = 'credit_positive'
    WHERE name IN ('apple_card', 'bilt_blue');

INSERT INTO schema_version (version) VALUES (4);
