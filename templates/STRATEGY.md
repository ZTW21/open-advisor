---
name: Master Strategy
description: The advisor's living master plan. Deep internal document. The user rarely reads this directly; the advisor reads it every time it's asked what to do next.
type: strategy
updated: 2026-04-17
stale_after: 35d
version: 0.0 (template)
last_reviewed:
  date: —
  routine: —
related:
  - goals.md
  - principles.md
  - rules.md
  - profile.md
  - state/net-worth.md
  - state/debts.md
  - state/income.md
  - memory/MEMORY.md
sources: []
---

# Master Strategy

*This file is the advisor's brain. It is rewritten — not appended to — on monthly, quarterly, and annual refreshes. See `routines/strategy-refresh.md` for the rewrite protocol.*

*How the advisor uses this file:*
- *Daily brief:* **does not** consult this file. Dailies observe; they don't advise.
- *Weekly summary:* reads **Next 30 days** to source its one nudge.
- *Monthly report:* reads all sections; rewrites **Next 30 days** and appends a History row.
- *Quarterly review:* rewrites **Next 30 days + Next 90 days + Next 12 months**.
- *Annual review:* rewrites everything, including **Long arc**.
- *Ad-hoc "what should I do this week?" / "am I on track?":* reads here first; never invents actions.

*Content rules (apply everywhere below):*
- Every concrete dollar figure must cite a CLI call or a source file.
- No specific tickers. Strategy / allocation / category / criteria only (per `CLAUDE.md §2`).
- Every action must be owned by the user — the advisor never commits itself to an action here.
- If a section is empty, leave the explicit **"_Empty — next refresh will populate._"** marker so the advisor knows it isn't stale data.

---

## Current stance

*One paragraph. The user's financial posture right now: where they are on the debt / cash / invest spectrum, the single most important thing currently true about their situation, the last routine that updated this.*

_Not yet initialized. Run onboarding (`routines/onboarding.md`) to populate the first draft._

## Next 30 days — the three things that matter most

*Exactly three. Each item must be (a) owned by the user, (b) concrete, (c) cited to a source, and (d) sorted by urgency × reversibility — irreversible damage (missed 401k match, high-APR debt accruing, expiring tax windows) first.*

*If the user completed an item mid-month, move it to `decisions/<slug>.md` and replace it at the next refresh — don't just delete.*

1. _Empty — next refresh will populate._
2. _Empty — next refresh will populate._
3. _Empty — next refresh will populate._

## Next 90 days

*Medium-term moves that aren't urgent this month but that the advisor should keep surfacing. Rebalance windows, tax-move timing, upcoming large expenses, open Roth space, HSA deadlines.*

- _Empty — next refresh will populate._

## Next 12 months

*Larger themes. Annual contribution targets, planned life events, debt-freedom dates, goal-pace checkpoints. Reconciled at quarterly; fully rewritten annually.*

- _Empty — next refresh will populate._

## Long arc (5+ years)

*Retirement trajectory, major-goal milestones with expected dates, payoff schedules, expected inflection points (kid to college, mortgage payoff, planned retirement). Rewritten at the annual review only.*

- _Empty — next refresh will populate._

## Dependencies

*Actions that unlock other actions. Format each as `trigger → unlocked action`. These let the advisor respond intelligently when the user crosses a threshold ("emergency fund hit 6 months → redirect the $X/month to taxable brokerage").*

- _Empty — next refresh will populate._

## Open questions

*Things the advisor wants the user to decide when they have time. Not urgent. Surface one at a time in weeklies when the moment fits.*

- _Empty — next refresh will populate._

## Open gaps

*Pulled from `memory/watchlist/` and from known-gaps entries in `state/insurance.md`, `state/estate.md`, `state/tax.md`. The advisor does not invent gaps — gaps live in source files and get rolled up here for visibility.*

- _Empty — next refresh will populate._

## What I'm *not* doing (with reasoning)

*Decisions not to pursue. Pulled from `goals.md § Not goals` and from `memory/preferences/`. This section prevents re-litigation: if the user says "I've decided I'm not aggressively saving for a house," that lives here with the date and the reason, so the advisor doesn't suggest it next month.*

- _Empty — next refresh will populate._

## History

*Every refresh appends one row. Never remove rows — this is the only log of how the strategy evolved. If a refresh touched only a subset of sections, list them.*

| Date | Routine | Sections rewritten | Summary of change |
|------|---------|--------------------|-------------------|
| —    | —       | —                  | Template state; awaiting onboarding. |
