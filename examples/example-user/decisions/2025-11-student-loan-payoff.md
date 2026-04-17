---
name: Student loan payoff
description: Killed the $9,100 Nelnet student loan balance early. Decision journal entry with full reasoning and downstream effects.
type: decision
decided_on: 2025-11-20
author: Alex (advisor co-drafted)
related:
  - memory/decisions/2025-11-student-loan-payoff.md
  - state/debts.md
  - accounts/ally-hysa.md
---

# Decision: pay off the Nelnet student loan early

**Date decided:** 2025-11-20.
**Date executed:** 2025-11-20 (same day — ACH from HYSA + bonus funds).

## The question

Should I pay off the remaining $9,100 student loan balance now, or keep to the standard amortization (scheduled payoff 2026-08)?

## The options considered

1. **Status quo.** Keep $220/mo payments at 5.5% APR. Loan ends 2026-08. EF rebuild stays the top windfall priority.
2. **Accelerate with bonus only.** Apply 60% of 2025 bonus (~$7,200) to loan principal. Still leaves a ~$1,900 remainder dragging into early 2026.
3. **Kill it today.** Combine 60% of bonus ($7,200) + $1,900 drawdown from HYSA. Loan gone this month. (Chosen.)

## Why option 3 won

- **Rate math.** Loan APR 5.5% vs HYSA APY 4.25% = net negative 1.25% carry on every dollar of HYSA that could be principal. Real dollars: ~$120/yr on the $9,100.
- **Interest saved.** Holding to 2026-08 = ~$185 in remaining interest per `finance payoff --account nelnet --to-zero`. Modest but real.
- **Cashflow.** The bigger benefit: $220/mo redirected. That's $2,640/yr. Over the CC payoff + EF rebuild horizon (~18 months), that cashflow is load-bearing.
- **Deductibility.** Alex's income crossed the student loan interest deduction phase-out in 2024, so the "keep the loan for the tax break" argument is gone.
- **Emotional.** Alex has been paying Nelnet since 2016. Finishing it is real motivation, not a rounding error. Weighted this explicitly — per `memory/preferences/debt-payoff-avalanche.md`, Alex's debt posture is math-primary but not math-only.

## Why not option 2

- Leaves a stub balance that costs full interest treatment without the psychological win of closing the account.
- EF drawdown of $1,900 is recoverable in ~4 months at current pace; the loan becoming zero is not recoverable — you're paying interest the whole time.

## What we're giving up

- **EF rebuild slows by ~$1,900.** Temporary: the freed $220/mo + bonus-sourced EF contribution in Q1 2026 recovers the drawdown by roughly April. Monthly reports will track this explicitly.
- **Loss of liquidity.** $1,900 of HYSA is gone until rebuilt. Risk: an unexpected expense between 2025-11 and 2026-04 would force CC use. Mitigant: CC has $15k+ available limit at promo APR, so the worst-case is uncomfortable, not catastrophic.

## Rule check

- `rules.md § Debt`: "pay down debt > 4% APR before optional investing." ✓ 5.5% > 4%, so this is consistent with the rule.
- `rules.md § Cash`: "keep $5k checking floor + EF above 3 months." ✓ after drawdown, HYSA still at ~$7.2k + $4k checking — 2 months of runway. Below the 3-month target but above the hard $5k floor.

## What we'll do next

1. **Monitor EF rebuild weekly for 2 months.** If it's not recovering as modeled, re-evaluate priorities.
2. **Redirect $220/mo freed cashflow to CC paydown** starting December 2025 statement. This moves CC projected payoff from ~late 2026 to 2026-08.
3. **Close `state/debts.md § Nelnet`** and move it to paid-off section.

## Looking back (added 2026-04-17)

As of this edit, 5 months after execution: EF rebuild back on trajectory (now $8,200; was $6,400 at low point in Dec). CC paydown on track for 2026-08 as projected. Decision still looks right.
