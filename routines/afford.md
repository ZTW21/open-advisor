---
name: Affordability Check
description: Full "can I afford X?" flow for purchases above ~$1,000 — cushion check, cashflow pace, goal impact, then a calm verdict.
type: routine
cadence: on trigger
output_length: short (6–10 lines)
updated: 2026-04-17
stale_after: never
related:
  - rules.md
  - goals.md
  - state/net-worth.md
  - routines/temptation-check.md
  - routines/loss-aversion.md
sources:
  - finance_advisor/commands/afford.py
  - finance_advisor/analytics.py (liquid_cash, trailing_monthly_outflow, goal_pace_impact)
---

# Affordability Check

Bigger purchases (a car, a trip, a home project) deserve a real check, not a gut feel. This routine runs the `finance afford` CLI, walks the payload, and gives a calm green/yellow/red verdict with the reasoning.

## Trigger

- "Can I afford $X?" for X ≥ ~$1,000
- "Can we do this trip?" / "Is it ok to replace the car?"
- User is considering a withdrawal from savings
- Temptation-check bounced up to this routine because the purchase is large

For smaller discretionary items under $500, prefer `routines/temptation-check.md`.

## Flow

### 1. Pull the payload

```
finance --json afford <amount> --min-months <3 or 6> --as-of <today>
```

`--min-months` default is 3. Prefer **6** if the user has volatile income (self-employed, commission, recent job loss) per `memory/facts/`.

Returns:
- `verdict`: `green` | `yellow` | `red`
- `cushion`: liquid cash before/after, monthly outflow, months of cushion before/after, minimum required
- `pace`: 90-day savings rate and monthly free cash estimate
- `goal_impact`: per-goal extra months before target

### 2. Read the verdict honestly

- **Green** — fits in one month's free cash and cushion stays above threshold. Say yes. Name the goal slip, if any. Don't pad.
- **Yellow** — dips into savings but doesn't breach the cushion. Say "yes, and here's what it costs." Translate the cost to days/weeks of goal slip.
- **Red** — breaches the cushion OR no outflow history. Don't say no reflexively; explain *why* it's red. Options to offer:
  - Pay over 2–3 months instead of at once
  - Delay until the cushion rebuilds
  - Use a specific account (e.g., a sinking fund) instead of general savings
  - Reduce scope (smaller trip, less expensive car)

### 3. Check rules and preferences

Read `rules.md` and `memory/preferences/` for anything that applies. Examples:
- "No withdrawal from emergency fund except for emergencies"
- "Pay cash for all vehicles"
- "Always fund the Roth first this year"

If a rule conflicts with an otherwise-green verdict, the rule wins.

### 4. Name one goal impact

From the `goal_impact` array, pull the highest-priority goal. Translate:

> "This pushes your emergency-fund target from November to December (per `finance afford`)."

Do NOT list every goal — pick the one that matters most.

### 5. Recommend

One or two sentences, honest about tradeoffs. Structure:
1. Verdict and *why* (reference the cushion or pace number).
2. One goal impact.
3. Optional alternative (for yellow/red).

### 6. Write-back on decision

If the user proceeds, log `decisions/YYYY-MM-DD-<purchase>.md`:
- Amount, reasoning, verdict, alternatives considered
- Which accounts funded the purchase

If the decision is surprising (breaks a pattern or a stated preference), write a note to `memory/decisions/` too — future sessions should know.

## Output shape

Example (yellow):

> Yes, you can afford the $3,000 trip — it dips into savings but keeps you at 3.5mo cushion vs. your 3mo floor (per `finance afford`). It pushes the emergency-fund target out by about 6 weeks (per `goals.md`). If you'd rather not touch savings, $750/mo over 4 months covers it from free cash — tell me which you prefer.

Example (red):

> I'd say wait on the $10,000 car for now. It would drop you to 0.6 months of expenses — well under your 3-month floor (per `finance afford`). Either push the purchase to September when the cushion rebuilds, or drop the budget to ~$4,500 which leaves you at 3.1 months. Your call; I won't pressure.

## Safety

- Never execute the purchase. Advise only.
- Never recommend specific financing products (credit cards, HELOCs) by name — talk in categories ("a 0%-intro-APR card for 12 months" is fine; naming a specific issuer is not).
- Dollar amounts come from the CLI output, not from context arithmetic.
- If the user is under acute stress (job loss, medical bill), route first through `routines/life-event.md` — don't run pure affordability math over a triage situation.
- No ticker recommendations. "Pay from the brokerage" is fine; "sell 12 shares of X" is not.
