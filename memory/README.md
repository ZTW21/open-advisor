---
name: Memory System — How It Works
description: Top-level guide for the advisor's memory folder. What goes where, how to write, when to update, how to retire. Not loaded into context by default — each subfolder README covers that folder.
type: folder-readme
updated: 2026-04-17
stale_after: 365d
related:
  - memory/MEMORY.md
  - CLAUDE.md
  - routines/memory-update.md
  - routines/consolidate-memory.md
sources: []
---

# Memory System

## Why memory

Memory is the difference between an advisor you like and an advisor you *trust*. A good human advisor remembers that you had a kid last year, that you paid off your student loans before investing even though the math didn't favor it, that you asked them to stop suggesting you cook more. The memory folder is how this advisor approximates that.

Memory is also the thing that keeps the advisor aligned across sessions. Without it, every conversation starts fresh — which means every opinion has to be re-argued from scratch. With memory, the user says something once and it sticks.

## What lives where

Six subfolders, each with a single purpose. Each has its own README describing what belongs there and the exact frontmatter to use.

| Folder | What goes there | Typical lifespan |
|--------|-----------------|------------------|
| `facts/` | Discrete, rarely-changing facts about the user — employer, household, health conditions, family support obligations. | Months to years. Update `last_confirmed` on reaffirmation; retire when stale. |
| `preferences/` | Philosophical statements the user has made about how they want their money handled. Override the Boglehead default in `principles.md` when they conflict. | Years. The user's philosophy is durable; don't churn these. |
| `feedback/` | Corrections the user has given about advisor behavior — what to stop doing, what to keep doing. | Indefinite. These are behavioral guardrails. |
| `decisions/` | Past decisions and the *reasoning* behind them. Prevents re-litigation. Different from the top-level `decisions/` journal, which records moves as they happen. | Years. Delete only if the underlying fact changed. |
| `watchlist/` | Time-sensitive things to surface later. CD maturities, pending cancellations, stated-but-unexecuted intentions. | Days to months. Delete once acted on. |
| `patterns/` | Behavioral or spending patterns observed from DB queries, not from user statements. Cite the query. | Months. Rewrite as patterns evolve. |

## The two-step write protocol

Every memory is a two-step write. Both steps are required.

**Step 1 — write the memory file.** Create a file under the right subfolder, using that folder's frontmatter template. The filename is semantic, not chronological — `chose-fidelity-over-vanguard.md`, not `2024-04.md`. Kebab-case, `.md`.

**Step 2 — add an index entry.** Add one line to `memory/MEMORY.md` under the appropriate section:

```markdown
- [Title](subfolder/filename.md) — one-line hook
```

If the index entry isn't there, the memory doesn't exist — future conversations won't find it. `MEMORY.md` is the only memory file that loads automatically.

## When to write

Write a memory the moment the user says something that will matter later and isn't already captured somewhere concrete (DB, `state/*`, `goals.md`, `rules.md`, `principles.md`, `profile.md`).

**Clear signals to write:**

- A philosophical statement ("I hate debt"). → `preferences/`
- A correction ("stop suggesting I cook more"). → `feedback/`
- A validated approach worth repeating ("the waterfall breakdown was helpful, keep using it"). → `feedback/` (success side)
- A durable life fact ("we just had a kid," "I caretaker my mom with $500/mo"). → `facts/`
- A decision with reasoning ("we're keeping the 30-year mortgage because we want payment flexibility"). → `decisions/`
- A pending action the user stated but hasn't executed ("I'm going to cancel Netflix"). → `watchlist/`
- An observed pattern from CLI output ("groceries drifted from $650 to $820/mo since last year"). → `patterns/`, cite the query.

**Signals NOT to write:**

- Current balances, transaction lists, account numbers — those live in the database.
- Things already captured in `rules.md`, `goals.md`, `principles.md`, `profile.md`, `state/*`. Reference them; don't duplicate.
- Ephemeral chatter ("let's look at this together"). If it's not useful next session, it's not a memory.
- Anything in the sensitive list below.

## Never write to memory

These never go into any memory file. Even if the user volunteers them.

- Account numbers (full). Last-4 is fine if truly necessary for disambiguation.
- Routing numbers, SWIFT codes, wire details.
- Social Security numbers, government IDs, driver's license numbers.
- Login credentials, passwords, security-question answers, 2FA seeds.
- Full street addresses. City or state is enough for tax purposes.
- Health diagnoses or medications, unless the user explicitly says "remember this so you plan around it" — and even then, capture the *planning impact*, not the medical detail.
- Protected attributes (race, ethnicity, religion, sexual orientation, immigration status) unless the user explicitly asks you to remember them.

If the user offers any of the above, decline: *"I don't save that — it lives at your bank / doctor / attorney."*

## How to update

A memory is a claim that was true when written. It can age.

**Reaffirmation.** When the user restates a preference or fact you already have, update `last_confirmed` to today. Don't create a new file.

**Evolution.** When a fact evolves (user changes jobs, gets a raise, pays off a debt), rewrite the relevant file rather than creating a new one. Git history preserves the old version.

**Contradiction.** When new info contradicts an existing memory, trust the new info and update. Say so to the user: *"I had you at Chase — updating that to Marcus."*

**Retirement.** When a memory no longer holds (user paid off the debt it was about, cancelled the subscription from watchlist), delete the file and remove its line from `MEMORY.md`. Don't leave tombstones.

## The MEMORY.md size limit

`MEMORY.md` is the only always-loaded memory file. It must stay small — target is under **50 lines of content** (frontmatter + blank lines don't count, but bullet lines do).

If it approaches the limit:
- Collapse related entries. Three "kids" facts can become one `household.md` entry.
- Retire stale watchlist items.
- Run the quarterly consolidation — see `routines/consolidate-memory.md`.

If `MEMORY.md` exceeds 50 lines, run consolidation *before* the next routine, not later.

## How memory interacts with other files

Memory is the *why*. The rest of the directory is the *what*.

- `rules.md` is the user's own guardrails — things they'd write on a whiteboard. Hard lines.
- `principles.md` is investing philosophy — defaults to Boglehead, editable by the user.
- `memory/preferences/` is the bridge: things the user stated that *override* the defaults in `principles.md`. When a preference conflicts with a principle, name the preference: *"You told me [verbatim] on [date], so we're sticking with that even though the default would say otherwise."*
- `goals.md` is active work. Goals don't go in memory; the *reasoning* for picking a particular goal (if non-obvious) might.
- `state/*` is current reality. Facts about the user's situation. Memory captures the *story* behind state, not state itself.

## How memory gets written in practice

Three cadences:

1. **During any substantive conversation** — when the user says something that fits the "when to write" list above, capture it in-flow. See `routines/memory-update.md` for the end-of-conversation sweep.
2. **During onboarding** — the onboarding script writes heavily into `memory/facts/`, `memory/preferences/`, and `memory/onboarding.md`. See `routines/onboarding.md`.
3. **During patterns observation** — daily/weekly/monthly routines write to `memory/patterns/` from CLI query output.

## How memory gets read

Three cadences:

1. **Every turn** — `memory/MEMORY.md` is always loaded. Skim it, follow links as they become relevant.
2. **On specific questions** — if the user asks about X and an index entry matches, read the memory file before responding.
3. **Before routines** — daily/weekly/monthly routines read the relevant subset (e.g., weekly reads `watchlist/` for items to surface).

## Verifying memory before you use it

A memory file is a point-in-time claim. Before recommending action based on a memory:

- If the memory names a specific account, fund, or rate, check it's still current (DB lookup, or ask).
- If the memory is older than six months and the situation is moving, ask: *"Last I recorded, you were [X]. Still the case?"* Update `last_confirmed` based on the answer.
- If current reality contradicts the memory, update the memory rather than trusting it.

## Failure modes to avoid

- **Writing duplicates.** Before writing a new memory, check whether an existing file covers it. If yes, update that file.
- **Over-writing.** Not every sentence is a memory. If it's not useful next session, skip it.
- **Stale MEMORY.md.** The index entry must match the file's title and hook. When you update a file, update its index line too.
- **Writing about us.** Memory is about the *user*, not the conversation. "I suggested X and they liked it" is feedback. "User likes waterfall breakdowns" is feedback. "We had a nice chat" is nothing.
- **Burying the lede.** Memory file bodies should lead with the rule or fact. Don't make future-you skim to find the point.
