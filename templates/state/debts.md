---
name: Debts
description: All liabilities with rates, minimums, and payoff order. Balances regenerated from DB; metadata hand-maintained.
type: state
updated: 2026-04-17
stale_after: 35d
regenerated: partial
generated_from: finance debts --json
related:
  - state/net-worth.md
  - goals.md
sources:
  - data/finance.sqlite
---

# Debts

*Populated during onboarding. Balances regenerated monthly from DB.*

## Active debts

| Account | Type | Balance | APR | Minimum | Payoff strategy |
|---------|------|---------|-----|---------|-----------------|
| — | — | — | — | — | — |

## Payoff order

*Default strategy: avalanche (highest APR first), unless the user has a preference in `memory/preferences/` that overrides it.*

1. _(empty)_

## Total debt

_Regenerated from DB. Not yet populated._

## Recent changes

_(payoffs, refinances, new debt — note the why)_
