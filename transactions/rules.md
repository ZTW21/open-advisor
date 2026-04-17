---
name: Auto-Categorization Rules
description: Rules that the importer uses to auto-categorize transactions. User-editable. More specific rules win over more general ones; user-defined rules beat defaults.
type: rules
updated: 2026-04-17
stale_after: 365d
related:
  - transactions/categories.md
sources: []
---

# Auto-Categorization Rules

*Rules are applied in priority order during import. First match wins. Anything unmatched gets flagged as "Uncategorized" for the user to resolve.*

## Rule format

Each rule has:
- **match** — a case-insensitive substring or `/regex/` against the normalized description
- **category** — the category to assign
- **priority** — higher priority evaluates first (default 100)
- **account_filter** (optional) — only applies to transactions from specific accounts
- **amount_filter** (optional) — only applies if amount meets condition (e.g., `>0`, `<-50`)

## Default rules (empty — added during onboarding and over time)

| Match | Category | Priority | Account | Amount |
|-------|----------|----------|---------|--------|
| _(example: `whole foods` → Groceries)_ | — | — | — | — |

## How to add a rule

When the advisor sees an uncategorized transaction during import, it asks: "Whole Foods $87 — category?" The user picks a category. The advisor asks: "Should I categorize all 'Whole Foods' transactions this way going forward?" If yes, a new rule gets added here.

## Special rules

- **Transfer detection** is handled by the CLI, not by rules here. Two transactions with equal magnitude, opposite signs, adjacent dates across two of the user's own accounts → flagged as a transfer pair.
- **Interest and fees** auto-categorize based on transaction type when banks report it in OFX.

## Maintenance

Review this file quarterly (see `routines/quarterly.md`) to retire rules that no longer match anything and refine rules that mis-categorize.
