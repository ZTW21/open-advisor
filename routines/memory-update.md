---
name: Memory Update Routine
description: End-of-conversation routine for capturing what you learned. Runs implicitly after any substantive exchange, explicitly when the user says "remember this" or at the end of onboarding / life events / windfall / big decisions.
type: routine
cadence: after every substantive conversation
output_length: none (writes to memory files, not a report)
updated: 2026-04-17
stale_after: 365d
related:
  - memory/README.md
  - memory/MEMORY.md
  - routines/consolidate-memory.md
  - routines/onboarding.md
sources: []
---

# Memory Update Routine

*Run this at the end of any conversation that produced new information. It's the step that makes memory actually accumulate.*

## When this runs

**Always, implicitly, at the end of a substantive conversation.** "Substantive" means the user told you something about themselves, their philosophy, their decisions, or corrected your behavior. Small-talk answers ("what's my net worth?") don't trigger this.

**Explicitly** when:
- The user says *"remember this,"* *"don't forget,"* *"make a note."*
- A routine concludes (onboarding, weekly, monthly, life-event, windfall, temptation-check, rebalance). Each of those routines ends with a call to this one.
- The user corrects a mistake or pushes back on advice — feedback memories are the single most valuable kind.

**Not when:**
- The user asks a pure question ("what does APR mean?") and nothing about them came up.
- The user is venting and hasn't actually said anything new about their finances or preferences.

## The scan

At the end of a conversation, scan back through the exchange and ask yourself these six questions, in order. Each maps to a memory subfolder.

### 1. Did the user state a philosophy?

*"I hate debt." / "I don't care about beating the market, I just don't want to lose." / "I want to help my parents even if it slows my own retirement."*

→ `memory/preferences/<slug>.md`. Frontmatter includes `stated_verbatim` with the quote. This is the most important category — these override defaults, so they must be faithful to what the user actually said.

### 2. Did the user correct your behavior?

*"Stop suggesting I cook more." / "Shorter weekly briefs." / "Don't harp on dining spend." / "I liked the waterfall — use that format."*

→ `memory/feedback/<slug>.md`. Write whether it's a **don't** (correction) or a **do** (success). Lead with the rule. Include **Why:** (the user's reason) and **How to apply:** (when this kicks in).

### 3. Did a durable life fact come up?

*"We just had a kid." / "I'm helping my mom with $500/mo." / "I have a chronic condition that shortens my planning horizon." / "I'm W-2 with RSU vesting quarterly."*

→ `memory/facts/<slug>.md`. Check for existing file first — if there's already an `employer.md`, update it rather than creating `employer-v2.md`.

### 4. Did the user make a decision and tell you why?

*"I chose Fidelity because the 401k is there and I'm not going to change." / "We picked 30-year over 15-year for flexibility." / "We're not pursuing rental property."*

→ `memory/decisions/<slug>.md`. The *why* matters most. Include `decision_date` and `revisit_if` (the condition that would warrant re-opening it).

### 5. Did the user mention something they intend to do but haven't?

*"I'm going to cancel Netflix." / "I'll move the Chase balance to the HYSA next week." / "I'm deciding by end of month whether to rent or buy."*

→ `memory/watchlist/<slug>.md`. Include `surface_by` (when to raise it — usually next weekly brief) and `expires` (when it becomes moot).

### 6. Did you observe a pattern from DB output?

*You ran `finance cashflow --last 90d` and noticed grocery spend climbing. You ran `finance account list` and noticed the user has three checking accounts.*

→ `memory/patterns/<slug>.md`. Include `source_query` with the exact CLI call that surfaced it. Rewrite when the pattern shifts; git history preserves prior versions.

## How to write (step by step)

For each item the scan identifies:

1. **Check for duplicates first.** Read the relevant subfolder's existing files (skim titles and descriptions in `MEMORY.md`). If one already covers this, update it:
   - Append to or rewrite the body as needed.
   - Bump `last_confirmed` to today.
   - If the body changed meaningfully, update the MEMORY.md hook to match.
   - *Do not create a new file.*

2. **If no existing file, create one.** Use the subfolder's frontmatter template (see each subfolder's `README.md`). File name is semantic, kebab-case: `prefers-debt-payoff.md`, `stop-cooking-suggestions.md`, `helps-mom-monthly.md`.

3. **Lead with the point.** The first line of the body must state the rule, fact, or preference directly. Future-you is skimming, not reading.

4. **Quote the user verbatim for preferences.** If it's a philosophical statement, capture their exact words in the `stated_verbatim` frontmatter field AND in the body. Preferences are load-bearing; paraphrase can drift.

5. **Add the index line to `memory/MEMORY.md`.** Under the appropriate section header. Format:
   ```markdown
   - [Short title](<subfolder>/<filename>.md) — one-line hook under 150 chars
   ```

6. **Never write sensitive identifiers.** Per `memory/README.md § Never write to memory`. If the user offered an account number or SSN, decline in your next message.

## The confirmation

At the end of the memory sweep, before closing the conversation, tell the user what you wrote:

> *"Before we wrap — I captured:
> - `preferences/prefers-debt-payoff.md` — your rule about paying debt before investing
> - `watchlist/netflix-cancellation.md` — I'll surface this in next week's brief
>
> Correct anything if I got it wrong."*

**Why this matters.** The user can catch misinterpretations while they're still easy to fix. It also teaches them that memory is a visible, editable part of the system rather than a black box.

Keep the confirmation short — a bullet per memory written. Don't confirm updates to `last_confirmed` only (those aren't content changes).

## Don't write to memory if...

- **The conversation hadn't hit the bar.** One-sentence factual questions don't need a memory write. If nothing about the user came up, skip the routine.
- **You're uncertain what they meant.** Ask first, write later. A badly-quoted preference is worse than no memory at all.
- **It's ephemeral.** "I'm in a bad mood" is not a memory. "I'm in a bad mood and want the weekly brief to be extra short this week" might be — as a temporary `feedback/shorter-briefs-april.md` with an explicit `expires` note, or just handled in-session.
- **It's sensitive.** Refer to the never-write list in `memory/README.md`.

## Size check before closing

Before ending the conversation, glance at `memory/MEMORY.md`:

- If it has more than **50 content lines** (count only bullets, not frontmatter/blank lines/comments), note it in a `watchlist/consolidate-memory.md` and plan to run `routines/consolidate-memory.md` within the week. Don't block the user's current task on consolidation.
- If it's approaching 45 lines, consider merging related entries *now* if you see obvious candidates (three `facts/kid-*.md` into one `facts/household.md`).

## Integrations with other routines

Every routine that ends a substantive conversation should explicitly call out to this one:

- `routines/onboarding.md § Section 9c` — writes heavily during the run; this routine finishes the job.
- `routines/life-event.md` — life events reshape facts and preferences; sweep carefully.
- `routines/windfall.md` — the decision of what to do with the windfall is a `decisions/` entry.
- `routines/temptation-check.md` — if the user declined a purchase, consider a `decisions/` or `feedback/` entry; if they bought anyway, note the reasoning for future calibration.
- `routines/rebalance.md` — any allocation decision is a `decisions/` entry.
- `routines/daily.md` / `routines/weekly.md` / `routines/monthly.md` — these produce `patterns/` entries from CLI output.

## Failure modes

- **"I'll remember to capture that later."** You won't. Capture in-flow.
- **Burying preferences inside decisions.** A philosophy statement belongs in `preferences/`, not in a decision narrative. If you write it in a decision, also write the preference.
- **Duplicate memories with slightly different names.** Check before creating. `employer.md` and `job.md` probably shouldn't coexist.
- **Index drift.** Every memory file needs a line in `MEMORY.md`. A file without an index line is invisible.
- **Quoting the advisor.** Memory is about the user's words and facts, not about things you said to them.
