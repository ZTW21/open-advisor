---
name: Loss-Aversion Check
description: Walk a user through a market-drawdown or portfolio-scare conversation without reinforcing panic or improvising changes. Leans heavily on the user's own rules and prior decisions rather than generic market commentary.
type: routine
cadence: on trigger
output_length: short (5–10 sentences)
updated: 2026-04-17
stale_after: never
related:
  - principles.md
  - STRATEGY.md
  - rules.md
  - memory/preferences/
  - memory/decisions/
  - routines/rebalance.md
  - routines/rules-enforcement.md
  - routines/mode-detect.md
sources:
  - finance_advisor/commands/networth.py
  - finance_advisor/commands/mode.py
---

# Loss-Aversion Check

Markets drop. The urge is to do something — usually the worst thing. This routine is the advisor's calm, evidence-based response to "should I sell?" / "the market's crashing — what do I do?" / "I'm scared about my 401k."

The short answer, almost always, is: *nothing new*. The long answer is the routine below — and it's the conversation that earns the right to say "hold."

## Trigger

- User expresses anxiety about market conditions, portfolio value, or a specific loss.
- User proposes a reactive move: "I want to move everything to cash" / "should I stop 401k contributions?" / "should I buy the dip?"
- A news event (recession headlines, bank crisis, policy shock) prompts "what should we do?"

## Flow

### 1. Acknowledge without reinforcing

Name that the concern is reasonable. Do not dramatize the market event. Do not list scary numbers. Do not predict what will happen next.

> "A 15% drawdown in a quarter is real — it happens every few years. What's going through your head?"

Keep it one sentence. Let the user talk if they want to.

### 2. Read principles and rules — quote, don't paraphrase

Open `principles.md` and `rules.md`. Quote back the parts that address exactly this moment. Almost every coherent investment policy has:

- A stated stance on market timing ("we don't time the market")
- A rebalance discipline ("we rebalance when drift > 5pp, not when headlines are loud")
- A contribution rule ("we contribute regardless of market conditions")

Cite verbatim — exact text, not paraphrase — using the format:

> Per `rules.md` § Investing: *"no market timing — dollar-cost average through downturns."*

The user wrote these rules during calm; they earn that calm's authority now. If the user's instinct in this turn conflicts with a rule, apply the explicit-conflict callout from `routines/rules-enforcement.md`. A panic-sell instinct doesn't get to slip past the market-timing rule unnamed.

If `rules.md` is sparse on this — e.g. all placeholders — say so and offer to add a market-stance rule *after* the scare passes. Don't use the calm of this conversation to write a new rule under duress.

### 3. Read past decisions — surface the nearest precedent

Scan `memory/decisions/` for prior market-event decisions (file names like `YYYY-MM-DD-market-scare.md` or `-drawdown-`). Surface the most relevant one — by recency or by resemblance to the current event.

Two precedents carry extra weight:
- Prior drawdowns where the user held and benefited.
- Prior drawdowns where the user sold and regretted it.

Quote the user's own words back to them where possible. If no prior drawdown decisions exist, note that — and commit to logging this one (step 7) so the next one has a precedent.

### 4. Pull the numbers the user actually owns

```
finance --json net-worth --as-of <today>
finance --json mode
```

The goal is not to compute the drawdown. It's to ground the user in what they actually have:

- Total net worth (not just the drop)
- Liquid cash (emergency fund — unaffected by markets)
- Monthly contributions going in (they'll buy cheap shares if invested regularly)
- Time horizon (retirement in N years — that's the relevant window)
- Current mode (`finance mode`) — if the user is in 'debt' mode, a market scare is even less relevant to them: their money isn't in the market yet. If in 'invest' mode, lean on the stated long-horizon philosophy. If in 'balanced' mode, say so honestly.

### 5. Name the tradeoff, don't decide

Two options, fair comparison:

| Action | Pros | Cons |
|---|---|---|
| Sell to cash | Prevents further paper loss | Locks in real loss; requires a reinvestment decision that's harder; taxable in brokerage |
| Hold (or buy at plan) | Captures rebound if/when it happens; consistent with written policy | Feels terrible; may drop further near-term |

Do NOT advocate for one. The user's own principles advocate for one already — your job is to remind them.

### 6. Offer one (1) action they can take that ISN'T market-timing

Productive moves that reduce the urge to panic-sell. Match the pick to the user's *mode* and *stated rules* — not to what sounds proactive:

| Situation | Suggested action |
|---|---|
| Tax-loss harvesting opportunity in taxable brokerage | Harvest losers; buy a similar-but-not-substantially-identical replacement. Never repurchase the same security within 30 days (wash-sale rule). Refer to a CPA at material amounts. |
| Allocation drift > tolerance per `finance rebalance` | Rebalance inside a tax-advantaged account (no tax). This is the *disciplined* answer — driven by drift, not by the headline. |
| Emergency fund below the rule in `rules.md` | Direct the next contribution toward cash, not equities. Highest-value place for new dollars is the fund below threshold. |
| Risk-tolerance mismatch was the real issue | Revisit the *target* allocation. This is a separate conversation from "markets are down" — follow `routines/rebalance.md`. |
| None of the above applies | Do nothing. "Doing nothing is a valid position" is worth saying out loud. |

Pick ONE. Don't present the whole menu — that creates the illusion of urgency and invites action-for-action's-sake. The advisor's job is to narrow, not expand, the choice set.

### 7. Log the conversation

Write `memory/decisions/YYYY-MM-DD-market-scare.md`:

```markdown
# Market scare: 2026-04-17

## What the user was feeling
- [user's own words, briefly]

## What we looked at
- finance net-worth (net: $X, cash: $Y)
- principles.md § Market conditions
- rules.md § Contribution discipline

## Decision
- Held allocation. Continued contributions on schedule.
- [Or] Rebalanced within 401k (no tax). [Or] Contributed extra to emergency fund to shore up cushion.

## Notes for future-me
- Next time this feeling comes up, re-read this entry first.
```

This is the single most valuable artifact of the routine. Three years from now, when the next drawdown hits, this file is evidence that the user has weathered this before.

### 8. Set a re-check window

Offer a check-in — not a market check-in, a *user-feeling* check-in:

> "Let's revisit in 30 days — I'll ping you then. By then one of two things is true: the drop is already recovering, or it's gotten worse. Either way, the answer is usually the same, and we'll have more evidence."

This is NOT a market timing window. It's a stress-management window. Concretely:

- Add the re-check to `memory/watchlist/market-scare-followup.md` with the date (30 days from today) and a one-line reference to the decision file from step 7.
- On the first weekly or monthly routine after the check-in date, surface the entry and ask how the user is feeling now. If the feeling has passed, close the watchlist item. If it hasn't, run the routine again — this time with *two* precedents (the original hold and the re-check).

If the user wants a shorter or longer window, honor it — but resist anything under 14 days. A window shorter than two weeks risks becoming a market-timing window in disguise.

## Output shape

5–10 sentences. No bullet lists unless the user asks for the tradeoff breakdown.

Example:

> I hear you — a 15% drawdown is uncomfortable, and this is the exact scenario most people regret acting on. Your `principles.md` says we don't time the market, and your contribution rule in `rules.md` says we keep buying regardless. Per `finance net-worth`, you still have a 5-month emergency cushion in cash (unaffected) and 28 years to retirement. The disciplined move is to hold and keep contributions going — you'll buy cheap shares this quarter. If the drop persists past a calendar quarter, we can rebalance within your 401k (no tax). I'll check back in 30 days. For now: nothing.

## What this routine does NOT do

- **Never names tickers** — this is a user-emotion conversation, not a security conversation.
- **Never predicts market direction.** "Markets usually recover within X months" is unreliable and beside the point.
- **Never endorses panic selling** — but also never lectures a user who did sell. If they already sold, skip to "what now?" (maybe tax-loss harvest, maybe dollar-cost back in).
- **Never encourages leverage as a buy-the-dip response.** "Buying the dip" with money you already have is fine per plan; borrowing to do it is a different category of risk.

## Safety

- If the user is in acute emotional distress tied to money (not ordinary anxiety — real fear or crisis), triage before planning (per `CLAUDE.md § 8`).
- If the user is under financial stress AND considering changes (job loss + market drop), route through `routines/life-event.md` first.
- Every dollar figure comes from `finance net-worth` or another CLI — no context math.
- Refer to a CPA for tax-loss harvesting at material amounts and to a financial planner or therapist if the emotional component is persistent.
