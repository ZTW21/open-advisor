---
name: Debts
description: All outstanding debts with APR, minimum payment, and payoff strategy. Cited by routines/debt-payoff.md and finance mode.
type: state
updated: 2026-04-01
stale_after: 30d
related:
  - accounts/chase-sapphire-cc.md
  - routines/debt-payoff.md
  - rules.md
sources:
  - finance_advisor/commands/payoff.py
---

# Debts

## Active

### Chase Sapphire Preferred
- **Balance:** $2,800 (as of 2026-04-01, per `finance balance --account chase_sapphire`).
- **APR:** 5.99% (promotional balance-transfer rate; expires 2026-12-01; default APR 19.99% thereafter).
- **Minimum payment:** $50.
- **Actual payment:** $400/mo (minimum + extra).
- **Projected payoff:** 2026-08 — well ahead of the 2026-12-01 promo expiration. `finance payoff --account chase_sapphire --extra 350` confirms.
- **Strategy:** avalanche order — this is the only active debt, so it's trivially first.

## Paid off (this year / recent)

- **Nelnet student loan — $9,100 balance, 5.5% APR.** Paid off 2025-11-20. Logged in `decisions/2025-11-student-loan-payoff.md`. That freed $220/mo that's now redirected into the CC paydown.

## Not currently active

- No mortgage.
- No auto loan (I drive a 2017 sedan, paid off).
- No personal loans or BNPL.

## Notes

- Per `rules.md § Debt`: no new credit card debt. The Sapphire balance is the last one.
- `finance mode` currently returns **balanced** — the 5.99% promo rate is below the 8% high-APR threshold, so this debt doesn't trigger debt mode. That's mechanical, not permissive: the CC is still the top active cleanup priority per `STRATEGY.md`, and if the promo rate weren't in place the posture would be different.
