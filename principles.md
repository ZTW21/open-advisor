---
name: Investing Principles
description: The user's investing philosophy. Ships with a Boglehead default; user edits during onboarding to match their actual views. When this conflicts with a stated preference in memory/preferences/, the preference wins.
type: narrative
updated: 2026-04-17
stale_after: 365d
related:
  - rules.md
  - goals.md
  - memory/preferences/
sources: []
---

# Investing Principles

*Default content below. During onboarding, the user reviews and edits. Preferences in `memory/preferences/` override these when they conflict.*

## Philosophy

**Index funds over stock picking.** We buy the market, not individual companies. Over long horizons, broad low-cost index funds consistently beat most active managers after fees.

**Costs matter more than returns you can't control.** We minimize expense ratios, trading costs, and tax drag. A 1% fee compounds into decades of lost growth.

**Time in the market beats timing the market.** We don't try to predict crashes or tops. We invest on a schedule and stay invested.

**Tax-advantaged first, then taxable.** We fill tax-advantaged space in priority order before taxable brokerage.

**Simple beats clever.** A three-fund or target-date portfolio beats elaborate strategies for almost everyone almost all the time.

**Emergency fund before investing.** Cash reserves come first. A 20% market drop matters less when you don't need to sell to pay rent.

## Priority of contributions

When allocating new savings each month, fill in this order:

1. **High-interest debt** (anything over ~6% APR) — pay down aggressively. Math wins here.
2. **Emergency fund** — target 3-6 months of essential expenses in a HYSA.
3. **401(k) up to employer match** — do not leave free money on the table.
4. **HSA** (if eligible) — triple tax-advantaged; treat as retirement when possible.
5. **Roth IRA** — up to the annual cap ($7,000 in 2026 for under-50).
6. **401(k) up to annual cap** — $23,500 in 2026 for under-50.
7. **Taxable brokerage** — after the above are full.

## Target allocation (default)

A three-fund portfolio, age-adjusted:

- **US total stock market:** (100 - age - 10)% _e.g. 30-year-old: 60%_
- **International total stock market:** (100 - age - 10)% × (20/70) _~17% for 30-year-old_

Wait — rewriting this more clearly:

Pick one of these frameworks:

**Option A — Age-based:** bond allocation = age − 20. Everything else split 70/30 US/international.
- 30-year-old: 10% bonds, 63% US stocks, 27% international stocks.
- 50-year-old: 30% bonds, 49% US stocks, 21% international stocks.

**Option B — Target-date fund:** one fund matching retirement year. Set and forget.

**Option C — Fixed three-fund:** 60% US / 30% international / 10% bonds. Rebalance annually.

The user picks one during onboarding. Edit this section to reflect the choice.

## Selected allocation

_Not yet selected. User chooses during onboarding._

## Rebalancing

Rebalance once a year, or when any allocation drifts more than 5 percentage points from target. Prefer rebalancing with new contributions (direct them to the underweight asset) over selling the overweight one — fewer tax consequences.

## Account placement

- **Bonds** → tax-advantaged accounts (they throw off taxable income).
- **International stocks** → taxable when possible (foreign tax credit).
- **US stocks** → anywhere (low ongoing tax drag from index funds).
- **REITs** → tax-advantaged.

## What we don't do

- No single-stock concentration above 5% of portfolio (see `rules.md`).
- No market timing.
- No leverage in retirement accounts.
- No options, crypto, or exotic products unless the user has explicitly accepted the speculative risk and it's capped.
- No advisor fees over 0.25% of assets.
- No loaded mutual funds.
