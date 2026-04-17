---
name: Monthly Report
description: How the advisor runs the one-page monthly check-in — net worth delta, savings rate, goal pace, top 3 actions. Always sourced from the CLI; regenerates state/net-worth.md.
type: routine
cadence: monthly (1st of each month, covers the prior month)
output_length: one page (~400 words)
updated: 2026-04-17
stale_after: never
related:
  - reports/
  - STRATEGY.md
  - routines/strategy-refresh.md
  - goals.md
  - state/net-worth.md
  - routines/weekly.md
sources:
  - finance_advisor/commands/report.py
  - finance_advisor/analytics.py
---

# Monthly Report

Once a month — on the 1st, covering the prior month — you produce a one-page summary that ties the week-level reality into the year-long plan. This is the check-in that can actually change behavior: it's long enough to show trends, short enough that the user will read the whole thing.

## Trigger

- On demand: user says "give me the monthly" or "how did March go?".
- This advisor is pull-based. If the user wants a monthly every 1st, a calendar reminder to ask is the right tool.

## Flow

### 1. Pull the payload

```
finance --json report monthly --month YYYY-MM
```

This returns:
- `totals` — inflow, outflow, net.
- `savings_rate` — income, spent, saved, rate (as a fraction).
- `net_worth` — beginning and ending net worth, delta, percent.
- `by_category` / `by_merchant` — top spending buckets.
- `budget_vs_actual` — categories with a budget row, showing planned vs. actual (pro-rated).
- `goals` — per active goal: current, target, expected-at-pace, and status (`green`/`yellow`/`red`/`info`).
- `anomalies` — large txns, new merchants, categories over pace.
- `month_over_month` — outflow comparison to the prior month.
- `suggested_actions` — a heuristic starting point you'll rewrite in voice.

### 2. Compose the page

Target length: ~400 words. Six sections, each short and cite-grounded.

1. **Net worth** — one sentence. "$X → $Y (+/- $Z). Context: driver is N."
2. **Savings rate** — one sentence. "Saved $A of $B earned this month — a **C.C%** rate." Compare to target if `rules.md` has one.
3. **Cash flow** — 2–3 sentences. Where the money went, where pace was notable. Cite `by_category`.
4. **Goals** — one bullet per active goal with the status dot. Keep to one line each.
5. **Notable moments** — one paragraph. The top anomaly or the MoM swing. If there's nothing noteworthy, say so in one line.
6. **Top 3 actions this month** — exactly three. Pulled from `STRATEGY.md`'s next-30-days and shaped by what the month just revealed. Strategy/allocation level, never tickers (CLAUDE.md §2).

### 3. Save the report

```
finance --json report monthly --month YYYY-MM --write
```

Writes `reports/YYYY-MM-monthly.md`. The CLI's default body is plain but factual; if you composed a richer version in your message, note that the canonical prose is the advisor's message and the CLI file is the numbers backup.

### 4. Update `state/net-worth.md`

The monthly run regenerates the narrative net-worth snapshot. Pull the ending net-worth figure from the payload, update the file's frontmatter `updated:` date, and rewrite the body paragraphs to reflect the new number, the monthly delta, and any account-level movements worth noting. Never write values from memory — always from `networth_at` in the payload.

### 5. Refresh STRATEGY.md

After writing the report, run `routines/strategy-refresh.md` at **monthly depth**. That routine owns the rewrite protocol — citation rules, version bump, History row, memory pass all live there. Monthly depth means:

- Rewrite **Current stance** and **Next 30 days**, plus **Open gaps** / **Open questions** if they changed.
- Leave **Next 90 days**, **Next 12 months**, **Long arc**, **Dependencies**, and **What I'm not doing** alone — those belong to the quarterly and annual cadences.
- Reconcile completed Next-30 items into `decisions/<slug>.md`; carry slipped items forward or retire them with reasoning.
- Append one row to the History table in `STRATEGY.md`.

Do not duplicate the rewrite rules here — delegate.

### 6. Memory pass

- If a category has been over pace for ≥2 months running, write `memory/patterns/<slug>.md`.
- If the user declined or completed a nudge, write `memory/decisions/<slug>.md`.
- Update `memory/MEMORY.md` with any new entries.

## Content rules

- ~400 words, hard ceiling. If you need more, it belongs in a quarterly.
- **Cite every number.** Every figure comes from the payload, referenced as `per finance report monthly`.
- **No tickers.** Talk about allocation, account types, and dollar moves — not specific securities.
- **Three actions, not more, not fewer.** If you can't think of three, the first two stand alone. If there are five, the two that didn't make it go into `STRATEGY.md`.
- **Honest about bad months.** If savings rate was negative, say so plainly. Don't soften with vague language.
- **Stale data disclosure.** If `net_worth.beginning_as_of` or `ending_as_of` is older than 10 days, flag it: "Net worth below is based on a snapshot from X days ago."

## Red/yellow/green rubric (for goals)

The CLI classifies goals automatically:
- **Green** — current is at or ahead of the linear pace to target by the target date.
- **Yellow** — behind pace but within 20% of the expected value.
- **Red** — more than 20% behind pace, or the target date has passed without completion.
- **Info** — no target amount or target date set; can't judge.

Don't override the status — re-surface it verbatim. If the user disagrees with a classification, that's a goal-definition discussion for next month, not a one-off override.

## Voice example

> **March 2026.** Net worth $247,832 → $254,710 (+$6,878, +2.8%). Savings rate was 22% this month — $1,540 saved on $7,000 income — ahead of the 15% target in `rules.md`.
>
> Spend was $5,460 (−$320 vs. February). Groceries held at $640 (on pace). Dining drifted to $420, third month over $350 — worth naming.
>
> Goals: 🟢 Emergency fund ($12k of $12k target, done). 🟡 Roth IRA ($3,200 of $7,000 by April 15). 🔴 Down payment fund ($38k of $60k by 2027-06 — pace suggests $52k).
>
> Notable: first time over $500 at Home Depot — the bathroom project you mentioned. Not an anomaly, just noting.
>
> **Actions for April:**
> 1. Bump the Roth IRA contribution from $400/month to $750/month — closes the gap with two cycles.
> 2. Test a dining cap of $350 for one month; if it holds, write it into `rules.md`.
> 3. Start the down payment conversation — either target date moves to 2028 or savings rate has to jump. Not a this-month decision, but let's surface it.

## Safety

- **Never compute totals yourself.** Always the payload.
- **Never recommend specific securities.** Strategy-level only (CLAUDE.md §2).
- **Never claim completeness.** If `suggested_actions` is empty, it means nothing obvious surfaced — still try to write three actions, but be upfront if one of them is a stretch.
- **Refer to a professional** for anything that touches tax optimization above the simple stuff, estate planning, or complex insurance.

## Useful sub-commands

| Task | Command |
|---|---|
| Last complete month | `finance --json report monthly` |
| Specific month | `finance --json report monthly --month YYYY-MM` |
| Save to reports/ | `finance --json report monthly --month YYYY-MM --write` |
| Net worth at date | `finance --json net-worth --as-of YYYY-MM-DD` |
| Month cashflow detail | `finance --json cashflow --month YYYY-MM --by category` |
| Month anomalies | `finance --json anomalies --since YYYY-MM-01` |
