---
name: Debt payoff — avalanche
description: Alex prefers mathematically-optimal (avalanche) payoff order over snowball. Cited by routines/debt-payoff.md when choosing a strategy.
type: preference
updated: 2025-08-22
stale_after: 365d
related:
  - rules.md
  - routines/debt-payoff.md
---

# Debt payoff — avalanche

**Preference:** when paying down multiple debts, attack highest-APR first (avalanche), not smallest-balance first (snowball).

**Why:** Alex said on 2025-08-22 — "I know snowball is supposed to feel better but honestly the math thing IS the motivation for me. Paying a dollar more in interest than I had to makes me more upset than finishing a small balance faster." Self-reported: seeing the interest line shrink is what keeps Alex engaged.

**How to apply:**
- Default `finance payoff` to `--strategy avalanche` unless Alex explicitly asks for snowball for a specific situation.
- If Alex ever has 3+ active debts and seems overwhelmed by the spreadsheet, it's okay to briefly surface that snowball exists — but don't push it. They've heard the pitch and chose avalanche.
- Don't re-litigate this every time a new debt appears. Refer back to this file.
