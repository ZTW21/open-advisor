---
name: Windfall Protocol
description: When income arrives that isn't regular — bonus, refund, gift, inheritance — apply the pre-agreed allocation instead of deciding in the moment.
type: routine
cadence: on trigger
output_length: short (4–8 sentences)
updated: 2026-04-17
stale_after: never
related:
  - memory/preferences/
  - goals.md
  - STRATEGY.md
  - routines/life-event.md
  - routines/debt-payoff.md
  - routines/rebalance.md
sources:
  - finance_advisor/commands/anomalies.py
  - finance_advisor/commands/payoff.py
---

# Windfall Protocol

The best time to decide how to use a windfall is **before** it arrives. The second-best time is calmly, once it's in the account. This routine locks in a pre-committed split the user made during onboarding (or on a prior windfall) — and walks through its application.

## Trigger

- `finance anomalies` flags a large inflow during import.
- User mentions: bonus, tax refund, gift, inheritance, settlement, stock sale, severance, or any non-recurring deposit.
- Import identifies an uncategorized large deposit ($2k+ typical threshold).

## Flow

### 1. Confirm it's a windfall

Not every large deposit is. Common confusables: transfers between accounts, reimbursements, security deposits returned, tax refunds that are actually owed amounts. Ask the user:

> "I'm seeing a $4,200 deposit on 2026-04-15 — is that the bonus you mentioned, or something else?"

If it's a transfer, categorize as internal and skip this routine.

### 2. Check for a protocol

Read `memory/preferences/windfall-allocation.md` (or similarly-named). A good protocol looks like:

> Standard windfall split:
> - 50% to current top-priority goal from `goals.md`
> - 30% to next unfunded tax-advantaged space
> - 20% guilt-free / lifestyle
>
> Override for windfalls > $10k: pause and re-run this routine (don't auto-apply).

If no protocol exists, *don't improvise.* Walk the user through creating one — see "First-time windfall" below.

### 3. Refine for the current situation

Even with a protocol, check for situation-specific overrides:

| Situation | Adjustment |
|---|---|
| High-interest debt exists | Redirect the "top goal" slice to debt per `routines/debt-payoff.md` |
| Emergency fund under target | Redirect the top slice to the emergency fund until rules.md floor is met |
| Rebalance has breach > 2× tolerance | Suggest part of the taxable-brokerage slice goes to the underweight asset class |
| Life event in progress (see `routines/life-event.md`) | Pause and triage first |

### 4. Compute specific dollar amounts

Run the arithmetic through the CLI. For a $5,000 windfall with a 50/30/20 split:

```
finance --json cashflow --last 90d       # get recent free-cash pace
finance --json payoff --extra <bonus/12> # optional: what does this do to debt pace?
```

Then present concrete numbers:

> "50% = $2,500 toward your emergency fund target.
>  30% = $1,500 to Roth (2026 contribution space remaining per `state/tax.md`).
>  20% = $1,000 guilt-free."

### 5. Flag tax implications

Run through the relevant ones — don't lecture, just name what applies:

- **Bonus** — flat 22% federal withholding often means under-withholding at year-end if the user is in a higher bracket. Suggest checking W-4.
- **Tax refund** — "you gave the IRS a 0%-interest loan for a year; want to adjust withholding to get this monthly instead?"
- **Inheritance** — step-up basis on inherited assets; potential estate tax at very large amounts. Refer to a CPA if it's material.
- **Stock sale / RSU vest** — cap gains owed; need to estimate for quarterly payments.
- **Settlement** — some are taxable (punitive damages), some aren't (physical injury). Refer to a CPA.
- **Gift** — generally tax-free to the receiver; gift tax (if any) is the giver's responsibility.

Don't invent numbers. For anything material, refer to a CPA.

### 6. Write the decision

Log `decisions/YYYY-MM-DD-windfall-<source>.md`:

```markdown
# Windfall: $5,000 Acme bonus (2026-04-15)

## Allocation applied
- $2,500 → emergency fund (top goal per goals.md)
- $1,500 → Roth 2026 contribution
- $1,000 → discretionary

## Reasoning
- Protocol per memory/preferences/windfall-allocation.md
- No override triggered (no acute debt, emergency fund on track, rebalance within tolerance)

## Tax note
- Bonus was withheld at 22%; user is in 24% bracket — may owe $50 at year-end. Flagged for Q2 adjustment.
```

### 7. Update memory if the protocol needs changing

If the user deviates from the protocol, update `memory/preferences/windfall-allocation.md` only if they say so explicitly. A one-time deviation is a decision, not a new preference.

## First-time windfall (no protocol exists)

Don't apply a default. Walk the user through creating the protocol:

1. **What role does this windfall play emotionally?** (Relief? Surprise? Recognition? The answer informs the "guilt-free" slice.)
2. **What's the user's gut split?** Write down verbatim. The user's instinct is data.
3. **Does the Boglehead default want different?** (Typical default: debt first → emergency fund to floor → tax-advantaged → goal → lifestyle.) Name the difference; don't override the user.
4. **Future-you test:** "If we get a $5k bonus next year, will this split still fit?" If not, refine now.

Save the final protocol to `memory/preferences/windfall-allocation.md`. Now future windfalls auto-apply.

## Output shape

4–8 sentences. Concrete numbers, one tax note, one action.

Example:

> Congrats on the $5k bonus. Applying your standard protocol (`memory/preferences/windfall-allocation.md`): $2,500 to emergency fund (closes 73% of the gap — per `goals.md`), $1,500 to Roth 2026 (leaves $5,500 contribution space), $1,000 guilt-free. Tax note: your employer withheld 22%; you're in the 24% bracket, so you might owe ~$100 at filing — small, but worth knowing. Want me to pencil the transfers for the weekend?

## Safety

- Never move money. The user executes.
- Never name specific securities to buy with a windfall.
- Large windfalls (>$50k) trigger a pause — this deserves a sit-down conversation, not a routine application. Refer to CPA/planner for very large amounts (e.g., inheritance from an estate).
- If the source is ambiguous (settlement, lawsuit), refer legal-tax questions to a professional before planning.
