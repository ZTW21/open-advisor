---
name: Consolidate Memory Routine
description: Quarterly (or trigger-based) pass over the memory folder to merge duplicates, retire stale entries, and keep MEMORY.md under 50 lines.
type: routine
cadence: quarterly, or when MEMORY.md > 50 lines, or on user request
output_length: short report (~100 words) listing what changed
updated: 2026-04-17
stale_after: 365d
related:
  - memory/README.md
  - memory/MEMORY.md
  - routines/memory-update.md
  - routines/quarterly.md
sources: []
---

# Consolidate Memory Routine

*A reflective pass over the memory folder. Merges duplicates, retires stale entries, and keeps the index tight. Run quarterly as part of `routines/quarterly.md`, or any time `MEMORY.md` exceeds 50 content lines.*

## When to run

- **Quarterly** — called from `routines/quarterly.md`.
- **On trigger** — any time `memory/MEMORY.md` has more than 50 content-bullet lines (frontmatter and blank lines don't count).
- **On request** — if the user says *"clean up memory,"* *"consolidate memory,"* or similar.
- **After onboarding** if the onboarding capture produced a lot of adjacent memories that should collapse into fewer files.

## Guardrails

- **This is a read-first, write-second routine.** Read every memory file before changing any. The merging decisions require seeing the whole set.
- **Prefer merging over deleting.** Deletion is for stale facts, completed watchlist items, and retired preferences. Consolidation is for three files that should be one.
- **Preserve verbatim quotes.** When merging two `preferences/` files that both have `stated_verbatim` fields, keep both quotes in the merged body with dates.
- **Summarize, don't drop.** If a memory is still load-bearing, it stays in some form. If it's truly moot, delete it — but say so in the report.
- **Show your work.** At the end, write a short report for the user listing what merged, what retired, and the new `MEMORY.md` size.

## The pass (step by step)

### Step 1 — Inventory

List every file under `memory/`, grouped by subfolder. Note each file's `written`, `last_confirmed`, and frontmatter `description`. Also read `MEMORY.md` and record which files are indexed and which aren't.

If you find a file that isn't in `MEMORY.md`: that's a drift bug. Decide whether it should be re-indexed or retired.

If you find an index line pointing to a missing file: remove the index line. Note it in the report.

### Step 2 — By subfolder, look for merges

For each subfolder, scan for files that should collapse.

**`facts/`** — merge when two files describe the same underlying entity:
- `kid-alex.md` + `kid-jordan.md` → `household.md` (one file, two kids named in the body)
- `employer.md` + `rsu-vesting.md` → `employer.md` (RSUs are an aspect of employer compensation)
- Don't merge unrelated facts just to shrink the count.

**`preferences/`** — merge when two statements express the same underlying philosophy:
- `prefers-us-equity.md` + `dislikes-international.md` → `prefers-us-only-equity.md` if both were said
- Keep separate if they're distinct philosophies, even if related.

**`feedback/`** — merge when two corrections are about the same topic:
- `shorter-weekly-briefs.md` + `shorter-monthly-briefs.md` → `shorter-briefs.md`
- Keep distinct if they're about different behaviors (e.g., "shorter" vs. "less scolding").

**`decisions/`** — rarely merge. Each decision usually deserves its own entry because the *why* is specific. Only merge if two "decisions" were actually the same decision reached incrementally.

**`watchlist/`** — see Step 3 (watchlist is mostly about retiring, not merging).

**`patterns/`** — merge when two patterns are actually one trend described at different points in time. Keep the latest observation and cite both source queries in the body.

### Step 3 — Retire stale

**`watchlist/`** — for each entry, check the `expires` field:
- If past expiry → delete the file and the index line.
- If the condition it tracks has been resolved (e.g., the Netflix cancellation watchlist was written and the subscription is now gone) → delete.
- If unactioned but still live → leave it, but surface it in this routine's report as *"Watch items still open: X, Y, Z."*

**`facts/`** — if `last_confirmed` is more than a year old and the fact depends on current circumstance (job, household), add a `needs confirmation` flag in the body and surface in the report. Don't delete unilaterally — ask the user.

**`preferences/`** — almost never retire. Philosophy is durable. Only retire if the user has explicitly reversed it (and then that reversal is itself a new feedback or preference entry: *"User previously preferred X; changed mind on <date> to Y"*).

**`decisions/`** — retire if `revisit_if` was met and the decision was actually revisited (the new decision is a new entry). Otherwise keep.

**`patterns/`** — retire if the pattern no longer holds after a year. Git keeps the history.

### Step 4 — Rewrite MEMORY.md

After Steps 2 and 3, rewrite `MEMORY.md` from scratch:

1. Keep the frontmatter. Update `updated` to today.
2. Keep the section headers (Facts, Patterns, Preferences, Feedback, Decisions, Watchlist).
3. Under each header, add one line per current memory file:
   ```markdown
   - [Title](<subfolder>/<file>.md) — one-line hook
   ```
4. The one-line hook should be ≤ 150 characters. If it needs more, either the memory title isn't sharp enough or the memory is doing too much — consider whether to split.

Target: **under 50 content lines.** If you can't get there without losing signal, surface it in the report and ask the user to reconsider which watchlist items matter.

### Step 5 — Write the report

Write a short report (under 150 words) to the user. Don't save as a file unless the user asks — just say it in the conversation. Structure:

> *"Consolidation pass complete.
>
> **Merged:**
> - `facts/kid-alex.md` + `facts/kid-jordan.md` → `facts/household.md`
>
> **Retired:**
> - `watchlist/netflix-cancellation.md` (cancelled 2026-03)
> - `patterns/grocery-growth-q1.md` (replaced by updated q1-q2 pattern)
>
> **Open watch items still live:** CD maturity 2026-06, tax extension decision.
>
> **MEMORY.md size:** was 58, now 42 lines.
>
> Anything I got wrong?"*

### Step 6 — Log it

Add one line to `decisions/YYYY-MM-DD-memory-consolidation.md` (the top-level `decisions/` journal, not the memory `decisions/`):

```markdown
---
name: Memory consolidation <date>
type: decision-journal
date: <YYYY-MM-DD>
---

# Memory consolidation — <date>

Ran `routines/consolidate-memory.md`. Before: N lines. After: M lines.

**Merged:** <list>
**Retired:** <list>
**Still watching:** <list>
```

This creates an audit trail so the user can see how memory evolved over time.

## Edge cases

**MEMORY.md was already tight (< 40 lines).** Still do the pass — catch stale watchlist items and `last_confirmed` dates worth bumping. Report is short: *"All clean. Size: X lines."*

**A file exists with no index line.** Either index it or delete it. Don't leave orphans.

**An index line points to a missing file.** Remove the index line. Note in report as *"cleaned up one broken index reference."*

**Two preferences contradict each other.** Don't merge silently. Surface to the user: *"I have two preferences on file that disagree: on 2025-06 you said X; on 2026-02 you said Y. Which is current?"* Then update based on the answer.

**Consolidation would drop user-quoted verbatim text.** Don't drop it. Either keep both quotes in the merged file's body, or keep both files.

## What this routine is NOT

- It's not a way to re-argue the user's preferences. Philosophies don't get consolidated into the advisor's preferred version. Capture faithfully; consolidate structurally.
- It's not a way to delete uncomfortable truths. If the user has a debt-payoff preference that makes them lose money on paper, that's still their preference. Keep it.
- It's not a periodic refactor. Memory files don't need stylistic cleanup. If the content is still right, leave it alone.

## Invocation from other routines

`routines/quarterly.md` includes a step:

> *Before writing the quarterly report, run `routines/consolidate-memory.md` if MEMORY.md > 50 lines OR it's been > 90 days since the last consolidation (check `decisions/` journal).*

Other routines can trigger it too (see `memory-update.md § Size check before closing`).
