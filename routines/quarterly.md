---
name: Quarterly Review
description: End-of-quarter ~2-page review. Rebalance check, fee audit, tax-posture check, goal recalibration, strategy refresh.
type: routine
cadence: quarterly (first week after quarter ends)
output_length: ~2 pages (~700–900 words)
updated: 2026-04-17
stale_after: never
related:
  - reports/
  - STRATEGY.md
  - routines/strategy-refresh.md
  - routines/rebalance.md
  - routines/consolidate-memory.md
  - principles.md
  - state/tax.md
sources:
  - finance_advisor/commands/report.py (quarterly)
  - finance_advisor/commands/fees.py
  - finance_advisor/commands/rebalance.py
---

# Quarterly Review

Once a quarter — in the first week after the quarter ends — you produce a ~2-page review that ties three months of data into the long plan. This is the check-in that can actually change allocations and fees, and it's where `STRATEGY.md` gets its deeper rewrite.

## Trigger

- Scheduled: 5th of each quarter's first month at 9am local (`0 9 5 1,4,7,10 *`), wired via `routines/schedule.md` as the `finance-quarterly-review` task.
- On demand: user says "give me the quarterly" or "how was Q1?".

## Flow

### 1. Pull the payload

```
finance --json report quarterly --quarter YYYY-Qn
```

Default (no flag) is the last complete quarter. Today is 2026-04-17 → the default is `2026-Q1`. The payload returns:

- `totals` — inflow, outflow, net over the quarter.
- `savings_rate` — income, spent, saved, rate.
- `net_worth` — beginning and ending, delta, percent.
- `by_category` / `by_merchant` — top spending buckets.
- `goals` — per active goal, red/yellow/green/info.
- `allocation` — current by-class percentages plus `targets` and per-class `drift`.
- `fees` — total annual fee cost, flagged accounts, `missing_fee_info`.
- `quarter_over_quarter` — outflow delta vs. prior quarter.
- `anomalies` — significant events from the quarter.
- `suggested_actions` — heuristic starting point.

If targets aren't set (`allocation.targets_set: false`), handle that inside step 3 below — don't stop the review.

### 2. Compose the page

Target length: ~700–900 words. Six sections, cite-grounded.

1. **Quarter in review** — one paragraph. What happened, financially and in life. Pull from `memory/facts/` and `memory/decisions/` if there's anything relevant to surface.
2. **Net worth and cash flow** — 3–5 sentences. NW start → end → delta. Inflow, outflow, savings rate, quarter-over-quarter.
3. **Rebalance check** — read `allocation.drift`. For any class with `|drift_pp|` over the user's tolerance (default 5pp), quote the number and recommend at the asset-class level (never tickers — CLAUDE.md §2). For in-tolerance classes, one line: "on target."
4. **Fee audit** — read `fees.flagged`. Translate expense ratios into annual dollars ("0.65% on $40k = $260/yr"). If `missing_fee_info` is non-empty, nudge the user to populate.
5. **Tax posture** — read `state/tax.md` for filing status and bracket. If Q4, pivot to year-end planning (Roth conversions, TLH, HSA contributions, charitable bunching). Earlier quarters, just flag: YTD tax-advantaged space used vs. the annual limit (401k, IRA, HSA) — numbers from the user, not computed.
6. **Goal recalibration** — bullet per goal with status dot. For red or yellow goals, translate the gap into a monthly contribution bump: "To hit $60k by 2027-06 from today's $38k, you need $1,833/mo from here — that's $400/mo more than current pace."
7. **Top 3 actions for the next quarter** — exactly three. Pull from `STRATEGY.md § Next 90 days` and shape by what this quarter revealed. Strategy-level only.

### 3. Save the report

```
finance --json report quarterly --quarter YYYY-Qn --write
```

Writes `reports/YYYY-Qn.md`. The CLI's default body is factual prose; the advisor's message is the canonical voice.

### 4. Refresh STRATEGY.md

Run `routines/strategy-refresh.md` at **quarterly depth**. That routine owns the rewrite protocol — citation rules, version bump, History row, memory pass all live there. Quarterly depth means:

- Rewrite **Current stance**, **Next 30 days**, **Next 90 days**, **Next 12 months**, **Dependencies**, **Open gaps**, **Open questions**.
- Leave **Long arc** and **What I'm not doing** alone unless this quarter produced a deliberate change (document the change in `decisions/` if so).
- Reconcile: completed 90-day items get `decisions/<slug>.md` entries; slipped items carry forward or get retired with reasoning.
- Append one row to the History table in `STRATEGY.md` and bump the version (e.g., 0.3 → 0.4).

### 5. Memory consolidation pass

Run `routines/consolidate-memory.md`:

- Merge duplicate memories.
- Retire stale entries (facts that no longer hold, preferences the user has walked back).
- Keep `memory/MEMORY.md` under ~50 lines.
- Re-confirm any `memory/watchlist/` items that have been sitting for a quarter — surface them if still unresolved.

### 6. Targets-not-set branch

If `allocation.targets_set: false`, do NOT fabricate targets in the review. Instead, in the Rebalance section, write:

> "No allocation targets are set yet. Current split (per `finance report quarterly`): US 62%, intl 14%, bonds 18%, cash 6%. Given `principles.md` (Boglehead default) and your age, a reasonable starting target is 50/20/20/10 — want me to seed that into `allocation_targets`?"

Then stop. Wait for the user. Per CLAUDE.md §5, DB writes need dry-run + confirmation.

## Content rules

- Cite every number. Every figure traces to the payload.
- No tickers. Asset-class and criteria only.
- Three actions, not more, not fewer. If you can only find two, two stand alone.
- If savings rate is negative or net worth dropped, say so plainly. No softening language.
- Stale-data disclosure. If any `ending_as_of` is more than 10 days behind the quarter end, flag it.

## Voice example (shape, not content)

> **Q1 2026.** Net worth $242,103 → $254,710 (+$12,607, +5.2%). Savings rate was 19% — $4,400 saved on $23,100 income — below the 22% quarterly target in `rules.md`. Q1 outflow ran $1,100 higher than Q4 2025, concentrated in holiday carry-over on Chase and a single home-repair event in February.
>
> **Allocation** is out of tolerance: bonds are 29% (target 20), so US equity is 8pp light. No tax impact if we do this inside the 401k — directing the next three months of contributions to the US-stock index fund would close the gap by late Q2.
>
> **Fees.** `finance fees` flags the Wealthfront brokerage at 0.65% expense ratio — on your current $38,400 balance that's ~$250/yr. Swap to a total-market index fund at 0.03% and that becomes ~$12/yr. Missing fee info on the Fidelity 401k — when you get a chance, pull the blended ER off the annual disclosure and we'll update it.
>
> **Tax posture.** YTD Roth contribution is $1,200 of $7,000 for 2026. HSA is empty. Nothing Q4-urgent; we'll revisit contribution pace at the monthly in April.
>
> **Goals.** 🟢 Emergency fund fully funded. 🟡 Roth 2026 behind pace (needs $1,450/mo from here to hit the cap by April). 🔴 Down payment fund ($41k of $60k by 2027-06) — current pace lands at ~$53k. Either the target date moves to 2028 or savings rate has to climb to 27%.
>
> **Actions for Q2:**
> 1. Redirect 401k contributions to US stock index for the next three cycles — closes the allocation breach.
> 2. Swap Wealthfront brokerage into a total-market index fund. Strategy-level move; saves ~$240/yr in fees.
> 3. Make the down-payment conversation an explicit decision by the May monthly: push the target year, or bump monthly savings. Not deciding IS a decision here.

## What this routine does NOT do

- **Never names tickers** (CLAUDE.md §2). Expense-ratio translation names the cost, not the instrument to buy.
- **Never projects market returns.** Drift is measured, not predicted.
- **Never writes to the DB without dry-run + confirmation** (CLAUDE.md §5). The only auto-writes are the report file in `reports/` and the STRATEGY.md refresh, per the carve-out.
- **Never does tax arithmetic beyond what the CLI surfaces.** For material tax moves, refer to a CPA.

## Safety

- Every dollar figure comes from `finance report quarterly` or another CLI. No context math.
- Flag stale data (CLAUDE.md §6) on any anchor older than 10 days.
- If the user is in financial stress (per `routines/life-event.md`), triage before running a routine review.

## Useful sub-commands

| Task | Command |
|---|---|
| Last complete quarter | `finance --json report quarterly` |
| Specific quarter | `finance --json report quarterly --quarter YYYY-Qn` |
| Save to reports/ | `finance --json report quarterly --quarter YYYY-Qn --write` |
| Fee audit only | `finance --json fees` |
| Rebalance payload | `finance --json rebalance` |
| Net worth snapshot | `finance --json net-worth --as-of YYYY-MM-DD` |
