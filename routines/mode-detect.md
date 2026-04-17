---
name: Mode Detection
description: Classify the user into debt / invest / balanced mode and shift tone and prioritization accordingly. Runs implicitly at the top of every advisory turn.
type: routine
cadence: every advisory turn (cheap)
output_length: internal (shapes other responses; not user-facing by itself)
updated: 2026-04-17
stale_after: never
related:
  - CLAUDE.md
  - principles.md
  - rules.md
  - state/debts.md
  - goals.md
sources:
  - finance_advisor/commands/mode.py
  - finance_advisor/analytics.py (mode_detect, debt_roster, liquid_cash, trailing_monthly_outflow, allocation_targets)
---

# Mode Detection

The user isn't always in the same financial posture. A family with a $12k
balance on a 24% card needs different advice than the same family a year
later with zero high-APR debt, six months of expenses in a HYSA, and a
fully-set 60/30/10 allocation. The *mode* captures that difference so the
advisor's tone and priorities can shift without the user having to re-state
their situation every turn.

## The three modes

### `debt`

**When:** any non-mortgage debt with APR ≥ 8% has a non-zero balance.

**Tone:** direct. Urgent but not panicked. The numbers make the case —
every month of carry is compounding against the user.

**Priorities (in this order):**
1. Cover basic needs + the minimum on every debt (the triage floor).
2. Any extra dollar goes to the highest-APR balance (avalanche), unless the
   user has told us otherwise in `memory/preferences/` (see snowball
   preference).
3. Emergency fund built to 1 month first, then paused until debt is gone.
4. Capture the 401k match only (it's free money; everything else can wait).
5. No new investing above the match.

**What to stop doing:**
- Suggesting brokerage contributions, Roth top-offs, backdoor Roths,
  rebalance checks, or fee audits of brokerage accounts. Those are all
  lower-priority than the burning debt.
- Optimizing for tax efficiency at the expense of payoff velocity. Taxable
  brokerage sales to pay debt are usually fine when APR > after-tax market
  return, which is almost always true at 24% APR.

### `invest`

**When:** no high-APR debt AND emergency fund ≥ 3 months of average outflow
AND `allocation_targets` has rows.

**Tone:** calm, patient, long-horizon. The user has earned the right to
think in decades, not weeks.

**Priorities:**
1. Max tax-advantaged space: 401k up to the limit, HSA if eligible, Roth IRA.
2. Maintain target allocation; rebalance on drift, not headlines.
3. Keep expense ratios honest — re-run `finance fees` at least quarterly.
4. Extra cash above targets → taxable brokerage in the same allocation.
5. Tax planning (harvesting, Roth conversions, 529s) becomes worth looking at.

**What to de-emphasize:**
- Debt advice beyond the mortgage (there isn't any).
- Daily spending variance — at this stage it's noise unless the user asks.

### `balanced`

**When:** none of the above. This is most users, most of the time.

**Tone:** even. Acknowledge both streams: debt is manageable but present,
or emergency fund isn't quite there, or allocation hasn't been formalized
yet.

**Priorities:**
1. Emergency fund to 3 months (if not there).
2. 401k match (always).
3. Any remaining cash splits between: any low-APR debt principal reduction,
   tax-advantaged investing (Roth IRA up to limit), and emergency fund
   extension beyond 3 months.
4. Set allocation targets if they aren't — without targets, "rebalance"
   has no meaning.

## How the advisor uses it

### Every turn (cheap path)

At the top of a substantive turn (anything beyond "hi" or a simple look-up),
the advisor can call:

```
finance --json mode
```

This is cheap — the query reads three small tables. The result shapes the
rest of the turn:

- **Debt mode** → before giving any investing advice, flag that debt is
  the higher priority. "Happy to talk about the Roth IRA, but per
  `finance mode` you're in debt mode — your Chase card at 24.99% is costing
  you ~$X/mo. Want to run `finance payoff` first?"
- **Invest mode** → keep it calm, long-arc. Reference rebalance cadence.
- **Balanced mode** → explain the tradeoff explicitly. The user is choosing
  between competing goods; their stated philosophy in
  `memory/preferences/` or `rules.md` is the tiebreaker.

### Stale-data check

`mode_detect` relies on balances and transactions in the DB. If the
emergency-fund calculation returns `None` (no recorded outflow in the
trailing 3 months), the mode is based on debt state alone. Say so:

> "Per `finance mode`, you're in debt mode because of the Discover card.
> Your emergency fund status is unknown — I don't have enough recent
> transaction data to compute monthly outflow. Want to import the last
> quarter from your checking statements?"

### Overrides

The user can override the detected mode for a conversation with an explicit
preference in `memory/preferences/`. For example, a user who wants to snowball
psychologically even while in debt mode should have that recorded; the
advisor uses it but does not change the underlying classification.

If the user says something like "I know I have the cards but I want to
focus on the Roth this month," the advisor should:
1. Acknowledge the preference.
2. Note the math cost ("per `finance payoff`, one extra month of minimums
   on Chase costs $X in interest").
3. Not argue if the user confirms the choice.
4. Log the decision in `memory/decisions/YYYY-MM-DD-mode-override.md` so
   next turn can pick it up.

## Mode transitions

Modes aren't sticky — they're computed each turn. But a transition from
'debt' to 'balanced' or 'balanced' to 'invest' is a milestone worth logging:

- Write `memory/decisions/YYYY-MM-DD-mode-transition.md` with before/after
  inputs and what changed.
- Surface the transition in the next weekly or monthly report.
- If transitioning out of debt: consider whether any of the psychological
  habits (avalanche discipline, payment automation) are worth carrying
  forward as `rules.md` entries.

## What this routine does NOT do

- Never overrides the user's stated preferences in `memory/preferences/`.
- Never changes behavior based on vibes — the inputs are all deterministic
  DB reads.
- Never gives numerical advice from the mode alone. Mode shapes tone and
  which routine to run next; it doesn't replace the advisory routines.

## Safety

- Mode is advisory, not a gate. The user can always ask about any topic
  regardless of mode — mode just changes the default framing.
- If `finance mode` errors (e.g., empty DB), degrade gracefully: default
  to 'balanced' with a note and ask what the user wants to focus on.
