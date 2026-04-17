---
name: Strategy Refresh
description: How the advisor rewrites STRATEGY.md on monthly, quarterly, and annual cadences (plus on life-events). The depth of rewrite scales with the cadence. Called by routines/monthly.md, quarterly.md, annual.md, and life-event.md.
type: routine
cadence: called by monthly / quarterly / annual / life-event routines, or on demand
output_length: rewrites STRATEGY.md in place + one History row
updated: 2026-04-17
stale_after: never
related:
  - STRATEGY.md
  - routines/monthly.md
  - routines/quarterly.md
  - routines/annual.md
  - routines/life-event.md
  - memory/MEMORY.md
  - goals.md
  - rules.md
  - principles.md
sources:
  - finance_advisor/commands/report.py
  - finance_advisor/commands/net_worth.py
  - finance_advisor/commands/cashflow.py
---

# Strategy Refresh

`STRATEGY.md` is the advisor's living master plan. This routine is the single source of truth for how that file gets rewritten. **Always rewrite the relevant sections — never append inline.** History is preserved in the History table and in git; everything else is replaced.

The depth of rewrite scales with the cadence. Don't over-rewrite: a monthly run that touches the long arc means you've either lost faith in last year's plan (say so explicitly, in a decision journal) or you're drifting.

## Scope by cadence

| Calling routine | Sections rewritten | Sections left alone |
|---|---|---|
| Monthly (`routines/monthly.md`) | Current stance, Next 30 days, Open gaps, Open questions (if changed) | Next 90 days, Next 12 months, Long arc, Dependencies, Not-doing |
| Quarterly (`routines/quarterly.md`) | Current stance, Next 30 days, Next 90 days, Next 12 months, Dependencies, Open gaps, Open questions | Long arc, Not-doing (unless the quarter produced a deliberate change) |
| Annual (`routines/annual.md`) | Everything, top to bottom. Bump the version field. | — |
| Life-event (`routines/life-event.md`) | Current stance + whatever the event invalidates. Life events can invalidate the long arc (e.g., inheritance, job loss, birth). | — |
| On demand (user asks for a full refresh) | Same as quarterly, unless the user asks for annual depth. | — |

The History table **always** gets a new row, regardless of scope. Listing "no change" is a valid entry — drift without action is itself a signal.

## Prerequisites

Before rewriting anything:

1. **Read `memory/MEMORY.md`** and skim any preferences/feedback memories that touch strategy. A preference to pay down debt even when math says otherwise (`memory/preferences/prefers-debt-payoff.md`) outranks the default order in `principles.md`.
2. **Read current `STRATEGY.md`.** Note which Next-30 actions got completed (they belong in `decisions/`) and which slipped (they probably carry forward).
3. **Pull live numbers from the CLI.** Never trust the last STRATEGY's numbers — they're a snapshot. Fresh queries:
   - `finance --json net-worth`
   - `finance --json cashflow --last 30d --by category`
   - `finance --json report monthly --month YYYY-MM` (if called from the monthly)
   - `finance --json report quarterly --quarter YYYY-Qn` (if called from the quarterly; Phase 10)
4. **Read `goals.md`, `rules.md`, `principles.md`, and the relevant `state/*.md` files.** Strategy is a reconciliation of live data against declared intent — you need both sides.

## Flow

### 1. Reconcile completed and slipped actions from the previous Next-30

For each of the three items in the current `Next 30 days`:

- **Completed** → write a short `decisions/YYYY-MM-DD-<slug>.md` if the decision mattered (not trivial adjustments). Cite the source that produced the action and the rationale that made it right.
- **In progress** → carry forward, but note it's a carryover. If it's a carryover for the second month, promote it to a sharper form ("open the Roth IRA" → "open the Roth IRA at a specific low-cost broker before Friday") or demote it out of Next-30 with an honest reason.
- **Slipped / abandoned** → ask the user *why* when you deliver the refresh. If they've genuinely changed their mind, record it in `memory/decisions/` and move the item to **What I'm not doing** with the date and reason. Don't silently drop items.

### 2. Rewrite Current stance

One paragraph. Include:
- A one-sentence descriptor of the user's posture (e.g., "Debt-paydown phase, emergency fund 70% funded, not yet investing outside the 401k match").
- The dominant constraint this refresh (cash-flow tight / capital-available / life-event-pending / etc.).
- A cited net-worth number from the payload. Format: `Net worth $X per \`finance net-worth\` (DB as of YYYY-MM-DD).`

### 3. Rewrite the sections the cadence says you own

**For every section, cite sources.** Example:

> **Next 30 days**
> 1. Redirect $500 from checking to the HYSA to top up the emergency fund to the 6-month target per `rules.md § Cash & liquidity` and `state/debts.md` expense baseline.
> 2. Open a Roth IRA at any major low-cost broker; contribute $7,000 before April 15 per `principles.md § Priority of contributions`. (Category: low-cost broad-market fund — no tickers per `CLAUDE.md §2`.)
> 3. Pay the full $420 on the Chase card before the statement closes on the 22nd per `rules.md § Debt`.

Rules for the **Next 30 days** block specifically:
- **Exactly three items.** Not two, not four. If there are only two genuine priorities, the third is a stretch item — say so in the item.
- Each must be owned by the user (not "the advisor will ..." — the advisor never executes anything per `CLAUDE.md §1`).
- Each must be concrete and dollar-specified where possible; citations mandatory.
- Sort by urgency × reversibility, irreversible damage first.
- Strategy/allocation level only. Never a ticker.

For **Next 90 days** and **Next 12 months**: bullets, not narrative. Each is a move or a checkpoint, cited to a source. Include timing ("before Q3 end", "by open enrollment") where applicable.

For **Long arc** (annual + life-event only): include (a) retirement trajectory with the pace number from the monthly's goal analytics, (b) major goal milestone dates, (c) payoff schedules for any structured debt, (d) one- or two-sentence narrative on the overall arc.

For **Dependencies**: `trigger → unlocked action`. Examples:
- `Emergency fund reaches 6 months of expenses → redirect $400/month from HYSA to taxable brokerage.`
- `Chase card paid off → reallocate the $250 minimum payment to the Discover card until that's paid.`

For **Open gaps**: pull from `memory/watchlist/` and from `known gaps` sections in `state/insurance.md`, `state/estate.md`, `state/tax.md`. Roll up, don't restate. One line each, with a pointer to the source.

For **Open questions**: things the advisor wants the user to decide but isn't urgent. Weekly briefs can surface one at a time when the moment fits.

For **What I'm not doing**: pulled from `goals.md § Not goals` and `memory/preferences/`. New entries require a date and a reason. Existing entries get confirmed (not re-asked) unless something in the last period contradicts them.

### 4. Append a History row

| Date | Routine | Sections rewritten | Summary of change |
|------|---------|--------------------|-------------------|
| `YYYY-MM-DD` | `monthly` / `quarterly` / `annual` / `life-event` / `on-demand` | List the sections touched | One sentence — what materially changed, or "no material change" if nothing did. |

Never delete prior rows.

### 5. Update the frontmatter

- `updated:` → today's date.
- `last_reviewed.date` → today's date.
- `last_reviewed.routine` → the calling routine name.
- `version:` — annual runs bump the major version (`1.0`, `2.0`...). Monthly/quarterly/life-event bumps the minor (`1.1`, `1.2`...). The version number is a quick sanity check for "how fresh is this plan?"
- `sources:` — list every CLI command whose output was used in this refresh, so the trace is auditable.

### 6. Memory pass

- If a Next-30 item is a new pattern (e.g., "redirect surplus to Chase card" has now been the top action for three months running), write a short `memory/patterns/<slug>.md`.
- If this refresh formally changed an allocation preference or a rule, write a `memory/decisions/<slug>.md` — don't bury the decision in STRATEGY's History column alone.
- Update `memory/MEMORY.md` with any new memory pointers.

## Content rules (invariants)

- **Rewrite, don't append.** If you find yourself writing "also" or "in addition," step back — the old content should have been deleted first.
- **No ticker names.** Strategy + allocation + category + criteria only, per `CLAUDE.md §2`.
- **Every dollar figure cites a CLI call or a source file.** If you can't cite it, don't state it. `_(to compute)_` is a legitimate placeholder — a fabricated number is not.
- **Never advise an action the advisor would take.** Every action in this file is owned by the user.
- **Honor memory overrides.** A stated preference in `memory/preferences/` wins over the default `principles.md`, every time.
- **Flag stale data.** If a cited source (`state/insurance.md`, `state/estate.md`, etc.) has `updated + stale_after` in the past, note it inline: *"— per `state/insurance.md` (updated 2025-09-01, may be stale)."*
- **Keep the file under ~300 lines.** If it grows beyond that, you're putting content that belongs in `decisions/` or `scenarios/`.

## Interaction with the calling routine

The calling routine (monthly, quarterly, annual, life-event) is responsible for:
- Delivering the user-facing narrative (the report itself).
- Pulling the live CLI payload.
- Calling into this routine to actually rewrite `STRATEGY.md`.

This routine is responsible for:
- The sectional rewrite rules above.
- The History row.
- The frontmatter update.
- The memory pass.

The split keeps the user-facing report short (the monthly is ~400 words; this file's rewrite is internal and much longer).

## On-demand refresh

If the user says *"let's refresh the plan"* outside a scheduled routine:

1. Ask *"Full refresh (everything) or just the next-30-days?"* Default to quarterly-depth unless they explicitly ask for annual.
2. Run this routine at the chosen depth.
3. Deliver a short summary of what changed: *"Rewrote Current stance, the 30-day list (two new items, one carryover), and the dependencies. Long arc unchanged. History row appended."*

## What this routine is NOT

- Not where the user-facing report gets written. That's `reports/YYYY-MM-monthly.md` etc.
- Not where detailed scenario analysis lives. That's `scenarios/`.
- Not a dumping ground for decisions. Meaningful decisions live in `decisions/<slug>.md` and `memory/decisions/`.
- Not a log. Use git history and the `## History` table for that — don't let prose accumulate.

## Common pitfalls

- **"Nothing changed this month, I'll skip the refresh."** No. Run it anyway; the History row can say "no material change." Skipping creates a gap in the audit trail.
- **"The old Next-30 item is still right, I'll leave it."** That's fine for the item — but rewrite the section anyway, re-source the citation, and confirm it's still true against the live CLI payload.
- **Plugging numbers from the previous STRATEGY into the new one.** Never. Pull every number fresh from the CLI. The previous file is context, not source.
- **Expanding scope mid-refresh.** If you started a monthly and find yourself wanting to rewrite the Long arc, stop. Close the monthly with a note ("flag: long arc may need revisit"), and bring it up in the next quarterly.
