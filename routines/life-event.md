---
name: Life Event Routine
description: Walk through the directory when a significant life event happens — marriage, divorce, birth, death, move, new job, job loss, inheritance, major medical.
type: routine
cadence: on trigger
output_length: varies
updated: 2026-04-17
stale_after: never
related:
  - profile.md
  - state/
  - memory/facts/
  - STRATEGY.md
  - routines/strategy-refresh.md
sources: []
---

# Life Event Routine

*General shape below — usable today. Per-event scripts (what to ask, what to decide, tax and insurance deadlines) fill in during Phase 9.*

## Trigger

The user mentions a significant life event. The advisor acknowledges it, gives space, then asks whether they want to update the directory now or later. If "later," write a `memory/watchlist/life-event-<YYYY-MM>-<event>.md` and revisit during the next weekly or monthly routine.

## Supported events (expand over time)

- Marriage / partnership
- Divorce / separation
- Birth / adoption
- Death of spouse or dependent
- Move (especially across states — tax implications)
- New job / raise / promotion
- Job loss
- Inheritance / windfall (may also trigger `windfall.md`)
- Major medical / disability event
- Buying or selling a home
- Retirement

## Flow (general shape)

1. **Acknowledge** — the emotional weight of the event matters; be calm, supportive.
2. **Triage urgent items** — anything time-sensitive (insurance enrollment windows, beneficiary updates, tax elections).
3. **Walk through the directory** — which files need updating? Typically:
   - `profile.md` — demographics, household
   - `memory/facts/` — new facts (new employer, new spouse, new kid)
   - `state/insurance.md` — coverage changes
   - `state/estate.md` — beneficiaries, will, POAs
   - `state/tax.md` — filing status, withholding
   - `goals.md` — re-prioritize
   - `STRATEGY.md` — refresh via `routines/strategy-refresh.md` at **life-event depth**: rewrite Current stance and whatever the event invalidates. Inheritance, job loss, birth, death, retirement can invalidate the Long arc.
4. **Surface pro-required items** — anything that needs an attorney, CPA, or HR conversation.
5. **Create a follow-up checklist** in `decisions/YYYY-MM-DD-<event>.md`.

## How to run it today (before per-event scripts exist)

Until Phase 9 fills in per-event detail, run the life-event routine by re-using the relevant sections of `routines/onboarding.md`:

- **Marriage / partnership** → Sections 1 (household), 2 (partner income), 3 (merged accounts), 5 (goals), 8a (add partner as beneficiary / health plan), 8c (wills/POA update).
- **Divorce / separation** → Sections 1, 3, 4 (debt split), 5 (re-prioritize goals), 8 (beneficiary update is urgent).
- **Birth / adoption** → Sections 1 (dependents), 5 (new goals — college, expanded emergency fund), 8a (life and disability insurance are often newly-critical), 8c (will, guardian named).
- **Death of spouse / dependent** → **pause and triage.** Say so directly: *"I'm so sorry. We don't have to do anything right now."* Surface free bereavement resources if it helps. When the user is ready: Sections 1, 3, 4, 8 in that order. Recommend legal/tax professional involvement.
- **Move** → Section 1 (state — affects tax), 8b (state tax re-estimate). Cross-state moves are a CPA conversation.
- **New job / raise / promotion** → Section 2 (income + match), 6 (contribution priority), 8b (withholding check).
- **Job loss** → **triage.** Section 2 updated to reflect loss, Section 4 (debt pace may change), emergency-fund rule from `rules.md § Cash & liquidity` becomes load-bearing. Mention free resources (unemployment, 211) if relevant.
- **Inheritance / windfall** → route to `routines/windfall.md`. Don't improvise.
- **Major medical / disability event** → Sections 1, 4 (medical debt), 8a (OOP max, HSA use), 8b (medical deduction thresholds). Consider CPA for large years.
- **Buying or selling a home** → Section 3 (account entry), 4 (mortgage), 5 (re-prioritize), 8a (home insurance), 8b (property tax + mortgage interest).
- **Retirement** → every section. This is a full re-onboarding — actually re-run `routines/onboarding.md` from the top.

Each event type will get its own dedicated sub-spec in Phase 9 covering: deadlines, tax elections, insurance enrollment windows, beneficiary urgency, and the specific decisions most people botch.
