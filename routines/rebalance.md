---
name: Rebalance Check
description: Compare current asset-class allocation to target; recommend rebalancing at the strategy/category level (never ticker level).
type: routine
cadence: quarterly (or on 5pp drift, or user-initiated)
output_length: short
updated: 2026-04-17
stale_after: never
related:
  - principles.md
  - accounts/
  - state/net-worth.md
  - STRATEGY.md
sources:
  - finance_advisor/commands/rebalance.py
  - finance_advisor/analytics.py (current_allocation, allocation_targets)
---

# Rebalance Check

The advisor reviews drift between current allocation and target, then recommends moves at the asset-class level. Never ticker-level. Never based on market timing.

## Trigger

- Quarterly routine includes a rebalance check.
- Any asset class drifts more than `tolerance` (default 5pp) from target — surfaced on monthly close.
- User asks: "how's my allocation?" / "should I rebalance?"
- New contribution is large enough that asking "where should this go?" deserves a rebalance-aware answer.

## Flow

### 1. Pull the payload

```
finance --json rebalance --tolerance 5 --as-of <today>
```

Returns:
- `targets_set` (bool) — whether `allocation_targets` rows exist
- `assets_total` — sum of eligible balances (liabilities excluded)
- `current_allocation` — list of `{asset_class, balance, pct, accounts}`
- `drift` — `current_pct - target_pct` per class, plus dollar drift
- `suggestions` — "reduce X by Npp (≈$D)" / "add to Y by Npp (≈$D)", sorted by magnitude
- `status` per class: `on_target` | `warn` | `breach` | `untargeted`
- `missing_balance_accounts` — accounts with no recorded balance (ignored)

### 2. If targets aren't set

If `targets_set: false`, don't invent them. Read `principles.md` with the user to pick a target split — typical Boglehead defaults (e.g., 60/30/10 US/intl/bonds for a moderate-aggressive portfolio; adjust for age and stated preferences).

Then populate `allocation_targets`:

```sql
INSERT INTO allocation_targets (asset_class, target_pct, active_from)
VALUES ('us_stocks', 50, '2026-04-17'),
       ('intl_stocks', 20, '2026-04-17'),
       ('bonds', 20, '2026-04-17'),
       ('cash', 10, '2026-04-17');
```

A helper CLI for this may land later. For now, the SQL goes through `finance` once the user confirms.

After seeding, re-run `finance rebalance`.

### 3. Read the drift

- **on_target** (within ±tolerance): quiet — say "on target" and stop.
- **warn** (between 1× and 2× tolerance): flag but don't urgently rebalance. Usually fixable by directing the next contribution to the underweight class.
- **breach** (> 2× tolerance): actively rebalance.

### 4. Prefer contributions over sales

Whenever possible, the advice is: *"direct the next N months of contributions toward [underweight class] until drift is under tolerance."* This avoids taxable sales and capital-gains tax drag.

Only recommend sales when:
- New contributions aren't enough to close a breach in a reasonable window (say, 2 quarters)
- A tax-advantaged account (401k, Roth, IRA) can do the rebalance with no tax impact
- The user explicitly asks to sell

### 5. Account placement nudges

From `principles.md` (Boglehead defaults):
- **Bonds** → prefer tax-advantaged (no drag on ordinary-income yield)
- **International stocks** → prefer taxable (foreign tax credit works there)
- **US stocks** → anywhere
- **REITs** → tax-advantaged

If current placement drifts from these rules-of-thumb, flag it but don't force a move. The math is small compared to the allocation decision itself.

### 6. Recommend at the strategy level

Good:
- "Reduce bonds by 7pp (~$3,500) in your 401k; bump international by 4pp and US by 3pp."
- "Direct your next 3 months of contributions 100% to international until drift < 5pp."

Bad:
- "Sell 12 shares of VTI." ❌
- "Rebalance because bonds just had a good quarter." ❌ (market-timing)
- "Move to 100% equities because the market's on a run." ❌

### 7. Write the plan

If the user commits to the rebalance, log `decisions/YYYY-MM-DD-rebalance.md`:
- Drift before
- Target split and tolerance
- Moves recommended (and whether through contributions or sales)
- Tax impact estimate, if any

Update `STRATEGY.md § Next 30 days` to include the rebalance action if it spans more than one contribution cycle.

## Output shape

Short. 4–8 lines of prose, or a tiny table when drift is material.

Example (within tolerance):

> Allocation is on target (per `finance rebalance`, 4/15/2026): US 51% (target 50), intl 19% (20), bonds 20% (20), cash 10% (10). Nothing to do. Next check during the July quarterly.

Example (breach):

> You're drifted (per `finance rebalance --tolerance 5`): bonds +9pp at $X, US −7pp, intl −2pp. Easiest fix: direct your next 3 months of 401k contributions to your US-stock fund and 1 month to international — closes the gap without any sales. If you'd rather rebalance now in the 401k (no tax), sell ~$3,500 in bonds there and buy the equivalent in the equity allocation.

## Target-sum warning

If `allocation_targets` doesn't sum to 100% (± 0.5pp), the payload surfaces a warning. Fix it before advising.

## What this routine does NOT do

- **Never names tickers.** Asset-class only.
- **Never executes trades.** Advises only.
- **Never recommends based on market forecasts.** No "shift to cash because of X event." We rebalance because *our allocation* drifted, not because we predict markets.
- **Never recommends complex tax-loss harvesting** without a human check; refer to a CPA if the user wants to harvest systematically.

## Safety

- Every dollar figure in the advice cites `finance rebalance`.
- If `missing_balance_accounts` is non-empty, surface those account names — the advice is only as good as the balances.
- Per `CLAUDE.md § 6`, flag stale data: if the latest balance used is >30 days old, say so.
