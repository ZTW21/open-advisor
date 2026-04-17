---
name: Debt Payoff
description: Plan a path to debt-free — pick a strategy (avalanche / snowball / custom), size the monthly extra, compute months-to-freedom and total interest.
type: routine
cadence: on trigger (monthly touch-in during close)
output_length: short (10–15 lines)
updated: 2026-04-17
stale_after: never
related:
  - state/debts.md
  - goals.md
  - principles.md
  - memory/preferences/
sources:
  - finance_advisor/commands/payoff.py
  - finance_advisor/analytics.py (debt_roster, simulate_payoff)
---

# Debt Payoff

The advisor's job on debt is: show the math, name the tradeoff, honor the user's stated philosophy. Avalanche is the mathematical default; snowball wins psychologically; either is fine if the user is consistent about it.

## Trigger

- User asks "how do I pay this off?" / "what's the fastest path?" / "should I do snowball or avalanche?"
- Monthly close surfaces a debt on the radar.
- Windfall routine needs a default application for surplus cash.
- New liability account added.

## Flow

### 1. Inventory the debts

```
finance --json payoff --as-of <today>
```

Returns the full roster (balance, APR, minimum payment, latest balance date) plus a default avalanche simulation with `extra=0`. If the simulation didn't converge, that's the first thing to flag — minimums aren't covering interest.

Before running the simulation with real numbers, verify APR and min_payment are populated for every debt. If not, edit them:

```
finance account edit <name> --apr <rate> --min-payment <amount>
```

Note: without APR, simulations treat the account as 0% (warning surfaced in the payload). That's only useful for modeling a 0%-intro card; everything else needs real APR.

### 2. Pick a strategy

Check `memory/preferences/` first.

| Strategy | Best for | Tradeoff |
|---|---|---|
| **avalanche** | math-first users; large APR spread | Slower early wins |
| **snowball** | users who need visible progress | ~more interest paid |
| **custom** | strategic reasons (e.g., bad-relationship card first, tax-deductible loan last) | Only as good as the order |

Default to avalanche unless `memory/preferences/` says otherwise. The difference on typical debt mixes is hundreds, not thousands — psychology usually wins if the user wavers.

### 3. Size the extra

Pull the monthly free cash estimate from **`finance cashflow --last 90d`** or from a recent `finance afford` payload. That's the envelope available for `--extra`. Common anchor points:

- Half of monthly free cash → sustainable; still leaves room for normal saving
- All of monthly free cash → aggressive; leaves no cushion; only recommended temporarily
- A specific dollar amount the user names → honor it

### 4. Run the simulation

```
finance --json payoff --strategy <avalanche|snowball|custom> --extra <amount> --compare
```

`--compare` runs the alternative strategy side-by-side so the user sees the interest difference. Use it once so they see the comparison; after that, run without it to keep output clean.

### 5. Translate the result

The payload returns months-to-freedom and total interest. Name three things:

1. **Months to debt-free** — and translate: "That's December 2028" not "34 months."
2. **Total interest** — absolute dollars, with the comparison if relevant.
3. **Which debt clears first** — and roughly when.

Example translations:
- "Chase clears in 14 months (June 2027), Discover in 27 months (July 2028)."
- "Total interest: $1,644. Snowball would cost $253 more in interest; avalanche saves you ~one dinner a month for three years."

### 6. Write the plan

Log to `decisions/YYYY-MM-DD-debt-payoff.md`:
- Strategy chosen and why
- Extra monthly amount
- Expected months-to-freedom and total interest
- Any deviation from default philosophy

Optional: write a memory at `memory/preferences/debt-philosophy.md` if the user expressed a strong view (e.g., "I want the Chase card gone first for emotional reasons, even if snowball is wrong").

### 7. Monthly touch-in

Each monthly close re-runs the simulation using fresh balances. If pace is ahead, say so. If pace is behind (balance not dropping as expected), flag for investigation — usually it's new charges on the "paid-down" card.

## Output shape

Short. 10–15 lines of prose + a quick table is fine.

Example:

> Plan: avalanche with $200/mo extra (per `finance payoff --strategy avalanche --extra 200`).
>
> - Chase (24.99% APR, $4,200): clears 21 months from now (~Jan 2028)
> - Discover (18% APR, $1,800): clears 27 months from now (~Jul 2028)
> - Total interest paid: $1,644
> - Snowball alternative: ~$253 more in interest over the same period
>
> Sustainable from your current free cash (per `finance cashflow --last 90d`, you're averaging $2,400/mo saved). Shall I check in monthly and flag if pace slips?

## What this routine does NOT do

- **Never executes payments.** You advise. The user moves money.
- **Never picks specific financing products.** "Consider a 0%-intro balance-transfer card" is fine; naming an issuer is not.
- **Never claims guaranteed numbers.** The simulation uses current APR and assumes no new charges — both can change. Surface those assumptions in the response.

## Safety

- Never recommend drawing from retirement accounts to pay debt unless the user explicitly asks about it. Even then, surface the 10% penalty + tax hit and refer to a CPA.
- If the user has a debt whose APR is lower than their expected investment return and they've flagged `memory/preferences/prefers-debt-payoff.md`, honor the preference. Don't re-litigate.
- If the simulation doesn't converge, be honest: "At $X/mo extra, we're not clearing interest on Chase. Either bump the extra to $Y/mo, or get an APR reduction call going first."
