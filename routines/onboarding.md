---
name: Onboarding Routine
description: Conversational flow that takes a new user from zero to a populated finance directory. Run once at the start; re-run on request when circumstances change significantly.
type: routine
cadence: once (initial); on request
output_length: 45–60 min full; 10–15 min quick
updated: 2026-04-17
stale_after: never
related:
  - profile.md
  - principles.md
  - rules.md
  - goals.md
  - state/net-worth.md
  - state/income.md
  - state/debts.md
  - state/insurance.md
  - state/tax.md
  - state/estate.md
  - accounts/
  - memory/onboarding.md
  - memory/MEMORY.md
  - memory/facts/
  - memory/preferences/
  - memory/README.md
  - routines/memory-update.md
  - STRATEGY.md
sources: []
---

# Onboarding Routine

This is the front door. The first time a user opens the advisor, this is what runs. It takes them from an empty directory to a populated seed state in **one conversation** — no homework, no forms, no jargon.

The deliverable is a finance directory the user can use *immediately*: populated profile, goals, rules, state files, accounts, and a first-pass `STRATEGY.md` they can read and push back on.

## Who this is for

- **First-time users.** Starting fresh. Run full mode.
- **Users with circumstances that shifted substantially.** Run from Section 5 (goals) onward. See also `routines/life-event.md`.
- **Users who abandoned a partial onboarding.** Pick up where they left off — check which files still have placeholder dashes and start there.

## Pre-flight (before you speak)

Before the first message:

1. **Check what already exists.** Read the frontmatter `updated` dates on `profile.md`, `goals.md`, `rules.md`, and `state/*`. If most files have been populated (no placeholder dashes), this isn't a fresh install — confirm with the user before overwriting.
2. **Check memory.** Read `memory/MEMORY.md`. If there's already a `memory/onboarding.md` with a non-`not-yet` `written` field, this user has onboarded before — offer to review rather than restart.
3. **Check principles.md.** It ships with Boglehead defaults. You will walk the user through these during Section 7; don't edit yet.

If any of the above suggests this is a re-run, open with: *"Looks like we've onboarded before. Want me to refresh what's changed, or start over?"* Otherwise, start fresh.

## Mode choice

Open with a mode choice. The user's answer sets the pace for the rest of the conversation:

> "Hi. Before we start, two choices:
>
> **Quick (10–15 min):** I ask the essentials — who you are, income, accounts, any high-interest debt, and one or two goals. You can fill in the rest later.
>
> **Full (45–60 min):** We go deeper — insurance, tax, estate, allocation framework, all your personal rules. By the end, you'll have a complete picture.
>
> Either is fine. Which do you want?"

- **Quick mode** runs Sections 1–5 and skips 6–9. Note which sections were skipped in `memory/onboarding.md` so the next conversation can pick them up.
- **Full mode** runs all nine sections.

## Principles for how you run this

- **One question at a time.** Never present a form. Never bulk-ask.
- **Warm and plain.** Never condescend. Never jargon without definition.
- **Quote the user.** When they say something philosophical ("I hate debt," "I'm not touching the market until it drops"), write it verbatim into `memory/onboarding.md` and later into `memory/preferences/`.
- **Don't require complete info.** If the user doesn't know their 401k contribution percentage, mark it `_(unknown — check pay stub)_` and move on. Come back to gaps at the end.
- **Confirm before writing.** Before creating a new file or writing a major passage, say what you're about to write and let the user correct it.
- **Never save sensitive identifiers.** Account numbers (last 4 fine, full never), SSNs, passwords, routing numbers. If the user offers them, decline: *"I don't save those — they live at your bank."*
- **No arithmetic in your head.** If you need a total (e.g., net worth from the balances the user just gave), invoke the CLI. Onboarding is a setup phase — it's fine to defer totals until after.
- **Pace.** After each section, offer a break: *"That was the employment section. Want to keep going, or take five?"*

---

# The nine sections

Each section below gives you: what to ask, how to probe, and exactly where to write the answer.

## Section 1 — Who you are *(~3 min)*

**Writes to:** `profile.md`, `memory/onboarding.md § Demographics & household`, `memory/facts/` (new files per durable fact).

**Questions (ask in order, conversationally):**

1. "What should I call you?" → write to `profile.md § Demographics › Name`.
2. "How old are you?" → `profile.md › Age`. Also create `memory/facts/age.md` (age matters for allocation, Social Security, catch-up contributions).
3. "Where do you live? State is what I care about — it affects taxes." → `profile.md › Location`.
4. "Who's in your financial life? Anyone whose money is tangled up with yours — spouse, partner, dependents?" → `profile.md › Household`, `profile.md › Dependents`. If partnered: *"Are we planning just for you, or the household?"* Record the answer as a memory: `memory/facts/household-scope.md`.
5. "Anything going on right now I should know about? Recent move, divorce, new kid, caretaking a parent, health event — doesn't have to be heavy, just context." → `profile.md § Major life context`. If the user mentions something that would trigger `routines/life-event.md`, note it and offer to re-run onboarding from the relevant section later.

**When done:** set `profile.md § Last life-event check` to today's date.

## Section 2 — Where you work *(~5 min)*

**Writes to:** `state/income.md`, `memory/facts/employer.md`, `memory/facts/income-type.md`.

**Questions:**

1. "Where do you work, and what do you do?" → `state/income.md § Sources › Primary § Source` + create `memory/facts/employer.md`.
2. "Are you W-2, 1099, self-employed, retired, or student?" → `state/income.md › Type` + `memory/facts/income-type.md`. This one matters a lot — it changes almost every recommendation.
3. "Roughly what's your gross annual income? Ballpark is fine." → `state/income.md › Gross annual`. If they hesitate: *"I only need a round number — $50k, $120k, $300k. This sets the scale."*
4. "How do you get paid — weekly, biweekly, monthly, irregular?" → `state/income.md › Pay cadence`.
5. "Rough take-home per month after taxes and deductions?" → `state/income.md › Net take-home monthly`. If unknown: *"Check one recent pay stub when you have a minute; I'll leave it blank for now."*
6. "Any other income — side work, rental, partner's income you want me to plan around, passive?" → `state/income.md § Sources › Secondary`.
7. "Have there been any big changes in the last year — raise, new job, job loss, business started?" → `state/income.md § Recent changes`. If yes, also write a `memory/facts/income-change-YYYY-MM.md`.

**When done:** if the user is W-2, ask *"Does your employer offer a 401(k) match? Do you know if you're capturing it?"* — this is a high-value early question. Capture the answer in `state/income.md § Withholding / tax handling` and in `memory/facts/401k-match.md`.

## Section 3 — What you own *(~10 min)*

**Writes to:** `accounts/<name>.md` (one per account), DB via `finance account add`, `state/net-worth.md § Current` (later — after Phase 4 balance entry).

**Framing:**

> "I want to know every place money lives — checking, savings, brokerage, 401k, IRA, HSA, real estate equity, anything. We'll go one at a time. I'll track them in a database so I can compute totals without asking you to do arithmetic."

**For each account:**

1. *Nickname* — e.g., `chase_checking`, `fidelity_401k`. Short, lowercase, underscores. Tell the user: *"Pick a short name — you'll refer to it later."*
2. *Institution* — e.g., Chase, Fidelity, Vanguard.
3. *Type* — pick from: `checking`, `savings`, `credit_card`, `brokerage`, `retirement`, `loan`, `mortgage`, `other`.
4. *Approximate current balance* — *"I don't need it to the penny. Ballpark."* → this gets entered as a `balance_history` row in Phase 4 (for now, note it in the account's markdown file).
5. *Opened when (year is fine)* — optional.
6. *Anything notable about it* → narrative for `accounts/<name>.md § Notes`.

**For each account, do two things:**

1. Run `finance account add --name <nickname> --institution <inst> --type <type>` via the CLI.
2. Create `accounts/<nickname>.md` using this template:
   ```markdown
   ---
   name: <institution> <type> (<nickname>)
   type: account-narrative
   account_id: <id from CLI>
   updated: <today>
   stale_after: 90d
   related:
     - state/net-worth.md
   ---

   # <institution> <type>

   - **Nickname:** <nickname>
   - **Institution:** <institution>
   - **Type:** <type>
   - **Opened:** <year or blank>
   - **Purpose / role in plan:** <narrative>
   - **Approximate balance at onboarding:** <ballpark>
   - **Notes:** <anything the user said>
   ```

**Common things to probe for, because people forget them:**
- Old 401(k)s from previous employers (often rollover candidates).
- Custodial accounts for kids.
- HSAs (easy to forget — they're often at a third institution).
- Employer stock (ESPP, RSUs — note as "employer stock" and flag to Section 7 on concentration).
- Crypto holdings on exchanges.
- Rental property equity (list as `other`; narrative explains).
- Cash at home (yes, really — if non-trivial).

**Do NOT probe for:** account numbers, routing numbers, passwords, login details.

**When done:** write the list of account nicknames to `memory/onboarding.md § Assets & accounts`.

## Section 4 — What you owe *(~8 min)*

**Writes to:** `state/debts.md`, DB via `finance account add` (type `credit_card`, `loan`, or `mortgage`), `memory/facts/debts.md` (one per meaningful debt with its why).

> "Now the other side — anything you owe. Credit cards, student loans, car loans, mortgage, 401k loans, medical debt, family loans — all of it."

**For each debt:**

1. *Which account is it on?* Match to something already added in Section 3, or add it now.
2. *Current balance (ballpark).*
3. *APR (interest rate).* If unknown: *"Check your last statement — the APR is on there. Most important number for debt."*
4. *Minimum monthly payment.*
5. *The story behind it.* Especially for consumer debt: *"What was the original purchase or life event?"* This goes in `memory/facts/debt-<name>.md` — not judgment, context. Strategy later depends on whether this is "one medical event" or "recurring lifestyle."

**Write to `state/debts.md § Active debts` as a table row per debt.**

**When done:**
- Sort by APR descending and write payoff order to `state/debts.md § Payoff order`. Default is avalanche; mention this and ask: *"Default approach pays highest interest first. Some people prefer paying the smallest balance first even when math says otherwise — snowball method. Which feels right?"* If they pick snowball or any non-avalanche rule, write `memory/preferences/debt-payoff-method.md` with the rule and the reason.
- If any APR is ≥15%, flag it explicitly: *"That Chase card is at 24.99% — that's costing you about $X per month just in interest. We'll want this to be a priority in the plan."* (Use the CLI for the $X computation once a balance exists.)

## Section 5 — What you want *(~8 min)*

**Writes to:** `goals.md`, `memory/onboarding.md § Goals (in the user's own words)`, `memory/facts/` if a goal reflects a durable life fact (e.g., "save for wedding in 2027").

> "Last section of the quick track — goals. What are you trying to do with money over the next 1–5 years? Could be building an emergency fund, paying off debt, buying a house, saving for a kid's college, retiring early, taking a sabbatical. Anything."

**For each goal the user names:**

1. *Name* — short, concrete. "Emergency fund," not "financial security."
2. *Target amount* — *"How much does it cost?"* If unknown: *"Rough number is fine — we can refine later."*
3. *Target date* — *"By when?"* Open-ended is OK; record as "someday" and mark priority lower.
4. *Why it matters* — one sentence in the user's own words. Quote them directly in `memory/onboarding.md`.
5. *Priority* — *"If you could only fund one goal this year, which would it be?"* Use their ranking to assign `high / medium / low`.
6. *Where the money lives (or will live)* — which account.

Write each as a numbered block under `goals.md § Active goals`.

**Also ask:**
- *"Anything you've decided you don't want to do — that I shouldn't keep suggesting?"* These go under `goals.md § Not goals`. Example: "I've decided I'm not going to aggressively save for a house — I like renting and moving." Respect these as hard constraints.
- *"Any goals you've been working on but paused?"* Go under `goals.md § Paused goals`.

**End of Quick mode.** If Quick was selected:

1. Write `memory/onboarding.md § Summary` — one paragraph covering: who the user is, what they earn, what they own/owe, what they're working toward.
2. Create `memory/facts/onboarding-mode.md` recording: "Ran quick onboarding on <date>. Sections 6–9 (principles, rules, insurance/tax/estate, allocation) deferred."
3. Write a first-draft `STRATEGY.md` (see Section 9 instructions — abbreviated version).
4. Thank the user and show them what got written: *"I've populated `profile.md`, `state/income.md`, your accounts, `state/debts.md`, and `goals.md`. Take a look when you have time. We can do a deeper pass any time — just say `run onboarding` from where we left off."*

**If Full mode,** continue.

## Section 6 — How you think about money *(~8 min)*

**Writes to:** `principles.md` (the user edits/confirms), `memory/preferences/*.md` (one per philosophical statement), `memory/onboarding.md § Philosophy & preferences`.

> "This section is less about numbers and more about philosophy. The advisor ships with a default investing approach — index funds, low costs, tax-advantaged first, don't try to time the market. Walk me through whether that fits you, or tell me where you disagree."

**Walk the user through `principles.md` one subsection at a time.** Read each section aloud (paraphrased), then ask: *"Sound right, or would you change that?"*

For each subsection:

- **Philosophy (Section heading):** if they push back on any of the six bullets, quote the bullet and record their edit as a preference memory. Example: user says "I think stock picking is fun and I want to do some of it" → write `memory/preferences/enjoys-stock-picking.md` with: *"User enjoys picking individual stocks and wants to reserve a budget for it. Recommend a 'play money' cap (e.g., 5% of portfolio per `rules.md`) rather than refusing."*
- **Priority of contributions:** confirm the order they're comfortable with. If they say "I don't care about 401k match because I don't plan to stay," record that as a preference; but also gently flag *"That's usually free money — happy to revisit if you want."*
- **Target allocation (Option A / B / C):** have them pick one. Write the choice into `principles.md § Selected allocation` in words: *"User selected Option B — target-date 2055 fund — on 2026-04-17."* If they're unsure, default to Option B (target-date) since it's the simplest.
- **Rebalancing:** confirm once-a-year or drift-based. Usually leave the default.
- **Account placement:** explain in plain English (bonds in 401k, international in taxable, US stocks anywhere). Confirm they're OK with it.
- **What we don't do:** read the list. This is important — these are the things the advisor will push back on. If the user wants to allow something from the list (e.g., "I want to hold crypto"), don't overrule them — move it to `rules.md § Investing` with their stated cap.

**Ask one open-ended question at the end:** *"Is there anything you believe about money that you want me to remember and enforce, even if the math says otherwise?"* This is the most valuable single question in the whole routine. Record whatever they say verbatim as a preference memory.

## Section 7 — Your own rules *(~5 min)*

**Writes to:** `rules.md`.

Walk through each subsection of `rules.md` as a prompt:

- *"What's your rule about emergency cash? How many months of expenses do you want liquid, no matter what?"* → `rules.md § Cash & liquidity`.
- *"What are your rules about contributions? What do you commit to doing every year, no matter what?"* → `rules.md § Contributions`.
- *"Rules about debt — hard lines you won't cross?"* → `rules.md § Debt`. Nudge toward "pay credit cards in full every month" if they don't volunteer it.
- *"Investing rules — anything you won't do, or won't exceed?"* → `rules.md § Investing`. Prompt for single-stock concentration cap, no-market-timing, no-leverage.
- *"Spending rules — any triggers you want in place?"* → `rules.md § Spending`. Suggest a "48-hour wait over $500" rule if they don't have one, but don't impose it.
- *"Big decisions — rules about buying a home, changing jobs, taking big risks?"* → `rules.md § Big decisions`.

**Don't fill this in preemptively.** Only record rules the user affirms. Empty sections are fine and mean "no rule yet."

## Section 8 — Insurance, tax, estate *(~10 min)*

**Writes to:** `state/insurance.md`, `state/tax.md`, `state/estate.md`. Gaps go to `memory/watchlist/`.

This section is the longest in Full mode. Pace it. If the user is flagging, offer to break it into a follow-up and deliver a `memory/watchlist/complete-onboarding.md` reminder.

### 8a. Insurance

For each of the six categories (health, life, disability, auto, home/renters, umbrella):

1. *"Do you have this?"* If no, note it in `state/insurance.md § Known gaps` — don't push, just record. You'll come back in a review.
2. If yes, capture the fields in `state/insurance.md`. *Skip premium amounts if the user doesn't know off the top of their head — not a blocker.*

Special probes:
- **Health:** is it HDHP? If yes, are they contributing to an HSA? → cross-check with Section 3's account list.
- **Life:** if they have dependents and no life insurance, flag it explicitly: *"With a kid in the house, no life insurance is a gap. Add it to the watchlist?"* → `memory/watchlist/life-insurance-gap.md`.
- **Disability:** often overlooked. *"Do you have long-term disability through work?"* — this is usually more important than life insurance for someone without dependents.

### 8b. Tax

1. *"Filing status for last year?"* → `state/tax.md › Filing status`.
2. *"Rough bracket — if you don't know, I can estimate from income."* Don't compute in your head. If user doesn't know, write `_(to compute from income)_` and leave it.
3. *"What was your AGI last year, roughly?"* → prior year section.
4. *"Any capital loss carryover or charitable carryover?"* → carryovers.
5. *"Do you use a CPA, software, or self-prepare?"* → who prepares. If anything complex (self-employed, multi-state, equity comp), recommend a CPA in one sentence: *"This is a good candidate for a one-time CPA consult."*

**Skip bracket/withholding detail if the user is glazing over.** Note as a watchlist item.

### 8c. Estate

1. *"Do you have a will?"* → `state/estate.md § Documents`. If no, note it. Don't lecture — one sentence: *"If you have dependents or significant assets, this is worth doing. We can revisit."*
2. *"Beneficiaries named on retirement accounts and life insurance?"* → beneficiaries. This is the single most impactful 30-minute task for most people and often the most neglected.
3. *"POAs — financial and healthcare?"* → designated people.
4. *"Guardian named for minor children?"* If they have minor kids and no guardian, flag it: *"Add as high-priority watchlist item?"*

**Do not give legal advice.** For anything beyond capturing state, say: *"Estate attorney territory — worth an hour with one."*

## Section 9 — Summary & first STRATEGY.md *(~5 min)*

**Writes to:** `memory/onboarding.md § Summary`, `STRATEGY.md` (full rewrite — first draft), `memory/MEMORY.md` (add pointers to every new memory file created).

### 9a. Summarize back

Write a one-paragraph summary of the user's posture and read it back: *"Here's what I heard. Correct me where I'm wrong:"*

> *"You're [age] in [state], [employment], earning ~$[income]. You own [account types] and owe [debt summary]. Top goal is [goal 1] by [date]. You believe [one or two philosophical statements quoted back]. Your hardest rules are [two or three from rules.md]. Biggest gap right now: [one — often insurance, will, or emergency fund]."*

Let the user correct. Write the corrected version to `memory/onboarding.md § Summary`. Set `memory/onboarding.md › written` frontmatter to today's date, `last_confirmed` to today.

### 9b. Write the first STRATEGY.md

Rewrite `STRATEGY.md` (don't append — replace) with this structure:

```markdown
---
name: Financial Strategy
description: The advisor's working plan for this user. Rewritten, not appended, on each routine refresh.
type: strategy
updated: <today>
stale_after: 90d
version: 0.1 (onboarding draft)
related:
  - profile.md
  - principles.md
  - goals.md
  - rules.md
  - state/
sources:
  - memory/onboarding.md
---

# Strategy — v0.1 (onboarding draft)

## Current stance (one paragraph)
<summary from 9a>

## Next 30 days — the 3 things that matter most
1. <action>
2. <action>
3. <action>

## Next 90 days
- <priorities>

## Next 12 months
- <larger themes>

## Long arc (5+ years)
- <retirement / major savings trajectory>

## Open gaps (things to revisit)
- <from watchlist and known-gaps lists across state/*>

## What I'm *not* doing (with reasoning)
- <decisions not to pursue, from goals.md § Not goals and memory/preferences/>
```

**Rules for the 30-day list:**
- Exactly three items. No more.
- Each must be concrete and owned by the user (never an advisor action).
- Each must trace to a specific source (`Per rules.md: ...`, `Per state/debts.md: ...`).
- Sort by urgency × reversibility: irreversible damage (e.g., missing 401k match, high-interest debt accruing) comes first.

**Don't do arithmetic in STRATEGY.md either.** If an action has a dollar amount, either cite a CLI call or mark it `(to compute)`.

### 9c. Index the memories

For every memory file written during this session, add a one-liner to `memory/MEMORY.md` under the appropriate section. Keep it under 50 lines total; if it's approaching that, collapse related entries.

### 9d. Close

Say:

> *"Done. I wrote:
> - `profile.md`, `goals.md`, `rules.md`
> - `state/` (income, debts, insurance, tax, estate — with gaps noted)
> - `accounts/` — one file per account
> - `memory/onboarding.md` and memory pointers in `memory/MEMORY.md`
> - A first-draft `STRATEGY.md`
>
> Look those over when you can. A few follow-ups I flagged:
> - [gap 1]
> - [gap 2]
> - [gap 3]
>
> When you're ready, next steps are:
> 1. Drop any recent bank statements in `transactions/inbox/` and I'll ingest them (Phase 5).
> 2. Or just ask me something — `what's my net worth?`, `can I afford X?`, `what should I do this week?`"*

---

# Minimum viable onboarding (the 10-minute version)

If the user can only spare ten minutes *right now* but wants something usable:

1. Name, age, state, household shape. *(1 min)* → `profile.md`
2. Employment type, rough income, any 401k match. *(2 min)* → `state/income.md`, `memory/facts/401k-match.md`
3. List the accounts (name + institution + type + ballpark balance). *(3 min)* → `finance account add` for each, create `accounts/<name>.md`
4. Any debt over 10% APR. *(1 min)* → `state/debts.md` (just the high-rate ones)
5. One goal. *(1 min)* → `goals.md § Active goals`
6. One rule they want enforced. *(1 min)* → `rules.md`
7. Summary paragraph + first `STRATEGY.md` with three 30-day actions. *(1 min)*

Record `memory/facts/onboarding-mode.md = minimum-viable on <date>; deferred sections 6–9`. Follow up in the next session.

---

# After onboarding — what should be true

Run this checklist before considering onboarding done:

- [ ] `profile.md` — no placeholder dashes in Demographics, Employment sections (other sections may be blank).
- [ ] `state/income.md` — at least a primary source.
- [ ] `state/debts.md` — either populated or explicitly "no debts" in the narrative.
- [ ] `goals.md § Active goals` — at least one goal.
- [ ] `rules.md` — at least one rule in some section (an empty `rules.md` is a real answer if the user has no rules yet — note that in `memory/onboarding.md`).
- [ ] One `accounts/*.md` per real account, matching `finance account list`.
- [ ] `memory/onboarding.md` — `written` and `last_confirmed` dates set.
- [ ] `memory/MEMORY.md` — has pointers to every new memory file written.
- [ ] `STRATEGY.md` — has a current-stance paragraph and a 30-day list.
- [ ] If `rules.md § Cash & liquidity` is empty AND user has no emergency fund, `memory/watchlist/emergency-fund.md` exists.
- [ ] **Cadence expectations set:** before closing, tell the user this advisor is pull-based — nothing runs automatically. Cadence reports (daily, weekly, monthly, quarterly, annual) all run when they ask; the user picks the rhythm that fits their life. If they want regular nudges, a phone/calendar reminder is the right tool.

---

# Common pitfalls

**The user dumps everything at once.** ("I'm 34, married, make 180k, have a mortgage and two IRAs and...") Don't try to write all of that in one turn. Ask them to slow down: *"Let me catch up — I want to get each piece right. Let's start with..."* and route them through the sections in order.

**The user won't commit to numbers.** ("I don't know what I earn.") That's fine. Write `_(to confirm)_` in the field, add to `memory/watchlist/`, and keep going. Perfection is the enemy of a usable first draft.

**The user gets defensive about debt or spending.** Do not lecture. Record, stay calm, and move on. The memory system remembers context so you can be honest later, when trust is higher.

**The user is in financial distress.** If onboarding surfaces imminent harm — eviction within days, utility shutoff, bankruptcy, medical debt they can't cover — pause the routine. Per `CLAUDE.md § The inviolable rules`, triage first: name the immediate risk, point to free resources (211, nonprofit credit counseling via nfcc.org), then offer to continue onboarding when the immediate crisis is addressed. Write `memory/watchlist/in-distress-YYYY-MM.md` with whatever you know.

**The user asks for security recommendations during onboarding.** ("What should I invest in?") Redirect: *"I stay at the category level — for example, 'a total-market index fund with expense ratio under 0.10%' — rather than naming a specific ticker. Let's finish onboarding and I can help you pick a fund family."* Per `CLAUDE.md § Specificity rule`.

**The user wants to put in precise balances.** Great — but don't block on it. For Phase 2, ballpark is enough. Precise balances are a Phase 4 activity (balance entry) and Phase 5 activity (import).

---

# When to re-run

- **Partial run:** the user bailed mid-onboarding. Resume from the last section with placeholder dashes.
- **Life event:** marriage, divorce, birth, death, move, job change, inheritance, major medical. Run `routines/life-event.md` (which reuses relevant sections from here).
- **Annual refresh:** as part of `routines/annual.md`, walk back through Sections 7 and 8 (rules and insurance/tax/estate) — rules and insurance drift.
- **User request:** *"Can we re-do onboarding?"* Always say yes. Offer to preserve current files (rename to `.bak-<date>`) before rewriting.
