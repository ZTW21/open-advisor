---
name: Windfall split — 60/30/10
description: Default allocation for unexpected inflows (bonus, refund, gift). Alex overrides with a written reason when it doesn't fit.
type: preference
updated: 2025-03-14
stale_after: 365d
related:
  - rules.md
  - routines/windfall.md
---

# Windfall split — 60/30/10

**Preference:** unexpected inflows default to:
- **60% to the current top financial priority** (right now: emergency fund rebuild → then credit card payoff).
- **30% to long-term savings** (Roth IRA if not yet maxed for the year; otherwise brokerage / 401k bump).
- **10% to "fun" / discretionary** — guilt-free spend on something they actually want.

**Why:** set 2025-03 after Alex got the 2024 bonus and said "I don't want to be the person who saves 100% of every windfall and then feels like none of the money is real. 10% on something nice is the tax I pay on being consistent the rest of the year."

**How to apply:**
- When a windfall hits (1099 payment > $1k, bonus, refund > $500, gift), quote this split back.
- The "top priority" bucket is not static — re-derive from `state/` and `goals.md` each time. Right now EF rebuild > CC payoff > Roth. This reshuffles as goals get hit.
- If Alex wants to override (e.g., "I want 100% to the CC this time because the promo is expiring"), honor it — but log the override to `decisions/` so we don't quietly drift off the rule.
- Already codified in `rules.md § Windfalls`. This memory captures the story behind the rule.
