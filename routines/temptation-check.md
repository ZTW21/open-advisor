---
name: Temptation Check
description: When the user asks "should I buy X?", run it against rules, cushion, cashflow, goals, and preferences before engaging with the idea.
type: routine
cadence: on trigger
output_length: 3-5 sentences
updated: 2026-04-17
stale_after: never
related:
  - rules.md
  - goals.md
  - memory/preferences/
  - routines/afford.md
  - routines/loss-aversion.md
sources:
  - finance_advisor/commands/afford.py
  - finance_advisor/commands/cashflow.py
---

# Temptation Check

When the user asks a variant of "should I buy X?" the advisor's job is a quick, calm check against the user's own stated rules — not a lecture, not a moralization. The answer is almost always "yes if you've already said so" or "wait because your own rule says wait."

## Trigger

- "Should I buy X?"
- "Is X worth it?"
- "Can I afford X?" → prefer `routines/afford.md` for larger purchases; this routine for smaller discretionary items or when the user has pre-committed rules that likely apply.
- "Talk me out of X" / "talk me into X" — same flow, but the user is telling you what they want the answer to be. Still give a calm check.

If the user names a security ("should I buy VTI?"), route to `principles.md` / rebalance — not here. Temptation-check is about spending, not investing.

## Flow

### 1. Check the rules

Read `rules.md`. Cite verbatim. Common rules that fire:
- 48-hour wait on discretionary purchases over $X
- "no new streaming subscriptions without canceling one"
- "dining out cap of $Y per week"
- "no luxury items until Chase card is paid off"

If a rule fires and says *wait*, the answer is wait. Don't override user rules just because they're convenient to override.

### 2. Check preferences and memory

Read `memory/preferences/` and `memory/feedback/` for anything that speaks to this purchase. Recent examples:
- `memory/preferences/prefers-debt-payoff.md` — user favors debt over investing even when math disagrees
- `memory/feedback/dont-lecture-on-dining.md` — user has asked not to question restaurant spending
- `memory/decisions/2026-03-guitar.md` — user already decided to save for this

If the user's *pre-stated* view covers the question, honor it.

### 3. Size the impact

Run **`finance cashflow --last 30d --json`** to get trailing pace, and for purchases >$200 also run **`finance afford <amount> --json`** for the cushion and pace breakdown.

Two numbers to name in the response:
- Where the purchase lands in this month's pace (on pace / over by $X / well under)
- What one month of that category looks like as a baseline ("Groceries is running $420/mo; this is ~1 week extra")

### 4. Translate to goal impact

Pull the top active goal from `goals.md`. Ask yourself: how many days/weeks does this purchase push that goal out? Phrase as a concrete translation — see `CLAUDE.md § Voice & style`.

> "This is ~3 weeks off your emergency-fund target" — not "this is 2% of your goal."

### 5. Answer in 3–5 sentences

Lead with the rule if one fires. Name the tradeoff. Give the answer.

Structure:
1. The rule / pre-committed preference (if any).
2. The impact on pace.
3. The tradeoff in days/weeks of a goal.
4. The recommendation — usually "honor your rule" or "your call, and here's what it costs."

### 6. Write-back when meaningful

- If the user acts on it (buys or skips), log it in `memory/decisions/` — especially if the reasoning was interesting or broke a prior pattern.
- If this is the *third* time a category has come up this month, flag a pattern in `memory/patterns/` (don't wait for the monthly routine).

## Output shape

3–5 sentences. Example:

> Your rule says $500+ gets a 48-hour wait (`rules.md`) — this is $720, so Saturday at the earliest. Pace-wise you're $80 under on discretionary for April (per `finance cashflow --last 30d`), so it wouldn't break the month. But it's ~3 weeks off your emergency-fund goal (`goals.md`). If you still want it Saturday, I'll pencil it in — otherwise I'd hold.

## What this routine is NOT

- **Not a lecture.** You're checking their rules against the purchase, not judging.
- **Not an investment decision.** "Should I buy VTI?" → rebalance routine, not here.
- **Not a yes/no on big purchases.** For anything >$1,000 or that touches a goal directly, run `routines/afford.md` for the full payload instead.

## Safety

- Never encourage purchases that the user's own rules or preferences forbid.
- Never moralize about discretionary categories the user has explicitly asked you not to question (`memory/feedback/`).
- Dollar amounts come from CLI output, not context arithmetic.
- Transfer flag: if the anomaly system flags the purchase as an unusual amount, surface that in the response.
