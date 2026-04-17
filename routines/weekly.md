---
name: Weekly Summary
description: How the advisor produces the ~150-word weekly summary — where you stand, one insight, one nudge. Always sourced from the CLI.
type: routine
cadence: weekly (Sunday evening or Monday morning)
output_length: ~150 words
updated: 2026-04-17
stale_after: never
related:
  - reports/
  - STRATEGY.md
  - goals.md
  - routines/daily.md
sources:
  - finance_advisor/commands/report.py
  - finance_advisor/commands/anomalies.py
  - finance_advisor/analytics.py
---

# Weekly Summary

Every Sunday evening (or Monday morning, whichever the user prefers) you produce a ~150-word summary of the week. This is the first meaningful check-in of the week — short enough to read during coffee, long enough that the user can course-correct.

## Trigger

- On demand: user says "how did this week go," "weekly recap," or asks for a summary.
- This advisor is pull-based — nothing runs on its own. If the user wants a weekly every Sunday, suggest a calendar reminder that nudges them to ask for it.

## Flow

### 1. Pull the payload

```
finance --json report weekly
```

Returns week totals, top 5 categories and merchants by outflow, pace vs. the prior 4-week median, and any anomalies. Add `--week YYYY-Www` for a specific ISO week.

### 2. Optionally pull more context

- `finance --json anomalies --last 7d` — if you want the full anomaly list, not just what `report weekly` surfaced.
- Read `STRATEGY.md` (next-30-days section) to source a nudge.
- Read `goals.md` for any pace check on active goals.

### 3. Compose the summary in four beats

Target ~150 words. One short paragraph per beat, or a tight two-paragraph structure — your call based on the week.

1. **Where you stand.** The net cashflow for the week, one number, plus pace vs. the 4-week median. Cite the payload.
   > "Net +$820 this week; outflow $2,140, which is 12% below your 4-week median."

2. **Top category signal.** The category most above or below pace. Name it, give the number, note the comparison.
   > "Groceries led at $380 — on pace. Dining was $160, third week over $120."

3. **One insight.** Something *noticed but not yet an action*. May trigger a write to `memory/patterns/`.
   > "That's three weeks of dining creep — worth flagging but not yet worth intervening."

4. **One nudge.** A single concrete thing the user can do this week — **pulled from `STRATEGY.md § Next 30 days`**, not generated fresh. Pick whichever of the three 30-day items best fits what this week's data just revealed. Specific at the strategy/allocation level — never a ticker recommendation (CLAUDE.md §2). If `STRATEGY.md § Next 30 days` is empty (template state), skip the nudge this week and flag that onboarding/strategy-refresh is overdue.
   > "This week: bump your 401k contribution from 8% to 10% if HR's window is open (per `STRATEGY.md § Next 30 days`)."

### 4. (Optional) Persist the summary

```
finance --json report weekly --write
```

Saves a markdown file at `reports/YYYY-Www-weekly.md`. The CLI's default is factual but dry; if you composed the prose version, note that the richer version lives in your message and the CLI version is the cold-numbers backup.

### 5. Memory pass

- If the week surfaced a **pattern** (recurring dining creep, missed automatic transfer, new merchant that's becoming a habit), write it to `memory/patterns/<slug>.md`.
- If the week includes a user **decision** (they said yes to upping the 401k, or they declined a nudge with reasoning), record it in `memory/decisions/<slug>.md`.

## Content rules

- ~150 words. Hard budget. A weekly that runs to 300 words means you're burying the signal.
- No tables in the prose version; the CLI payload has them.
- Cite every number. "$2,140 outflow (per `finance report weekly`)." Concise inline citations are fine.
- No ticker names, no buy/sell advice on specific securities.
- If nothing noteworthy happened, say so in one line and move on. Don't pad.

## Voice examples

*Calm week:*
> "Net +$680 this week; outflow $1,920, in line with your 4-week median. Top category was Groceries at $340 (on pace). Nothing unusual — Netflix posted, payroll hit Friday. One nudge: your emergency fund is $200 short of the 6-month target per `goals.md`; a single transfer from checking this weekend closes it."

*Busy week:*
> "Net −$320 this week — outflow $3,100, 28% over your 4-week median. Driver: $540 at Home Depot (first time over $200 there), plus three dinners over $100 each. The Home Depot charge looks one-off; the dining pattern is the third week in a row. One insight: dining is now 1.4x your trailing average. One nudge: if the Home Depot was for the bathroom project (per `memory/facts/`), record it in `decisions/` so we don't double-count it in next month's pace."

## Safety

- **Don't compute totals yourself.** Every number comes from the payload.
- **Transfers are excluded by default** in the cashflow numbers — that's deliberate. If the user asks "where did the money go," don't include internal transfers.
- **Don't recommend securities.** "Bump your 401k" ✅. "Buy VTI" ❌ (CLAUDE.md §2).
- **Flag stale data.** If the latest transaction is older than two days, surface it in the summary.

## Useful sub-commands

| Task | Command |
|---|---|
| This week payload | `finance --json report weekly` |
| Specific week | `finance --json report weekly --week YYYY-Www` |
| Save to reports/ | `finance --json report weekly --write` |
| Full anomaly list | `finance --json anomalies --last 7d` |
| Cashflow by merchant | `finance --json cashflow --last 7d --by merchant` |
