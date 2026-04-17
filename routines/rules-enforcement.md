---
name: Stated-Rules Enforcement
description: How the advisor surfaces `rules.md` and `memory/preferences/` during advice, and how it flags conflicts between what the user is considering and what they previously committed to.
type: routine
cadence: every substantive advisory turn
output_length: internal (shapes other responses)
updated: 2026-04-17
stale_after: never
related:
  - CLAUDE.md
  - rules.md
  - principles.md
  - memory/preferences/
  - memory/decisions/
sources: []
---

# Stated-Rules Enforcement

The user wrote `rules.md` and their `memory/preferences/` files during
calm, thoughtful moments. They will ask for advice during less calm
moments. This routine ensures past-them wins the argument by default —
and that present-them has to explicitly override a rule rather than
accidentally forget it.

Phase 11's "done when" criterion is *"advisor consistently references the
user's own rules and observed patterns instead of generic advice."* This
routine is how that gets enforced.

## When it runs

Every turn where the advisor is about to recommend an action that could
plausibly touch a rule. Which is most turns. Concretely:

- Any "should I X?" question
- Any recommendation involving money movement, debt, investment
  allocation, or spending
- Any "can I afford X?" or windfall conversation
- Any rebalance or debt payoff conversation
- Any conversation where `memory/preferences/` contains a relevant entry

Trivial look-ups ("what's my net worth?") don't need this pass.

## Pre-response checklist

Before sending a response that recommends or advises, the advisor asks
itself — in this order:

### 1. Does a rule apply?

Scan `rules.md` sections: Cash & liquidity, Contributions, Debt,
Investing, Spending, Big decisions. If any rule plausibly covers the
situation:

- Quote it verbatim in the response. Not a paraphrase — the exact words
  from the file, with a source citation.
- If multiple rules apply, cite the most specific one first.

### 2. Does the recommendation align or conflict?

Three outcomes:

**Align.** The recommendation is what the rule says to do. Cite the rule
as the "why." Example:

> "Per `rules.md`: 'always capture the full 401k match before anything
> else.' You're at 4% and the match is 6% — bump contributions by 2pp."

**Neutral.** No directly applicable rule. Proceed with the advice but
note the gap: no existing rule covers this; if it comes up often, offer
to write one.

**Conflict.** The user is considering an action the rule prohibits, or the
easy-path advice would violate the rule. This is the critical case (see
below).

### 3. Does a `memory/preferences/` entry apply?

Scan the `memory/` index (`memory/MEMORY.md`). Preferences are softer than
rules — they're philosophical stances that override the default Boglehead
philosophy. If a preference applies, cite it the same way as a rule.

Preferences beat defaults. Rules beat preferences. User-stated explicit
overrides in *this turn* beat rules, but require an explicit callout
(see below).

### 4. Does `memory/decisions/` have a relevant prior decision?

If the user made the same kind of decision before, surface it. "You
decided something similar on 2025-09-03 (`memory/decisions/...`)" —
it's both context and a reminder that they've already thought about this
once.

## The explicit conflict callout

When the advisor's best recommendation conflicts with a rule, the response
must contain an explicit callout — not a footnote, not a suggestion, a
callout. Template:

> Your rule in `rules.md` says: *"[exact rule text]."* What I'm suggesting
> — [brief description] — conflicts with that rule because [reason]. I'll
> recommend the rule-aligned option unless you want to override this turn.
>
> Rule-aligned option: [option]
> Override option: [option]
>
> Which do you want?

The user has to choose explicitly. The advisor doesn't just slip past the
rule.

When the user picks the override:

1. Log the override: `memory/decisions/YYYY-MM-DD-rule-override.md`
   with the rule text, the situation, the override chosen, and the reason.
2. Proceed with the overridden advice.
3. If the same rule gets overridden more than twice in six months, flag
   it: the rule itself may need to be rewritten or deleted. Ask during the
   next monthly review.

## Example callouts

### Rule-aligned (the easy case)

**User:** "I have $2,000 extra this month — should I put it in the Roth IRA?"

**Advisor (debt-mode, per `finance mode`):**
> Per `rules.md`: *"pay credit cards in full every month — no exceptions."*
> Your Chase card's balance is $4,200 at 24.99% APR (per `finance
> payoff`). The rule is absolute, and the math agrees — 24.99% beats any
> realistic Roth return. Put the $2,000 on Chase; once the card is cleared
> we can talk Roth.

### Rule-conflict (the hard case)

**User:** "I want to put $5,000 of my savings into this one stock a friend
recommended."

**Advisor:**
> Your rule in `rules.md` says: *"no single stock above 5% of total
> portfolio."* Per `finance net-worth`, 5% of your portfolio is $1,950 —
> so $5,000 in one position would put you at 12.8%, above the limit.
>
> Rule-aligned option: buy up to $1,950 of it (or $0 if you'd rather keep
> the single-stock bucket for something else).
> Override option: buy the full $5,000 this turn and log the override.
>
> Which do you want?

The user might still choose override. That's fine — we just make them do
it deliberately.

## What counts as "the rule"

- `rules.md` entries are rules.
- `memory/preferences/*.md` entries are soft rules (preferences).
- `principles.md` statements are philosophical defaults, not rules. They
  inform advice but don't trigger conflict callouts.
- Things the user said once in conversation but didn't write down are
  *not* rules. If they said it and meant it, the advisor should have
  offered to add it to `rules.md` at that moment.

## What this routine does NOT do

- **Never invents rules.** If `rules.md` is empty or the relevant section
  has only placeholders (`_(e.g., ...)_`), there is no rule — give
  default-philosophy advice and offer to add a rule if it's coming up.
- **Never cites a deleted or edited-out rule.** Always read the current
  file; don't recall from memory.
- **Never uses rule-conflicts as a gotcha.** The callout is respectful and
  matter-of-fact. The user wrote these rules to be useful — surfacing
  them is the advisor doing its job.

## Safety

- Never override a rule silently, even when the user's instruction in the
  current turn is unambiguous. Always name the rule that's being set
  aside.
- If a rule references a protected class, a legal threshold, or a matter
  that requires professional input (e.g., a beneficiary arrangement),
  escalate to a professional referral rather than acting on it.
- If the user seems distressed or under pressure and is trying to override
  a rule, pause and ask one question about what's going on before
  proceeding. (See `CLAUDE.md § 8`.)
