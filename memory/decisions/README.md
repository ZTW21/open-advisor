---
name: Decisions Folder Guide (memory)
description: Guide for writing memory/decisions/ entries. Not loaded into context by default.
type: folder-readme
---

# Decisions (memory) — what goes here

Past financial decisions and **the reasoning behind them**. Prevents re-litigation. Different from the top-level `decisions/` folder (which is a journal of moves *as they happen*); this is the compressed "why" for long-term reference.

**Examples:**
- `chose-fidelity-over-vanguard.md` — "Moved 401k to Fidelity in 2024 — employer match, better UX, not revisiting for 5+ years"
- `no-529-until-2030.md` — "Decided to prioritize retirement over college savings until 2030 when kids are closer to college age"
- `kept-mortgage-30yr.md` — "Chose 30-year over 15-year in 2022 — wanted payment flexibility, committed to extra principal payments instead"
- `no-rental-real-estate.md` — "Decided rental property isn't a fit — doesn't want the management overhead"

**When to write:** when the user makes a non-trivial decision and tells you the reasoning. Also when they tell you about a *past* decision and reasoning that would otherwise be re-opened every year.

**Frontmatter template:**
```yaml
---
name: <decision name>
description: <one-line summary>
type: memory-decision
written: <ISO date>
last_confirmed: <ISO date>
decision_date: <ISO date of when the decision was made>
revisit_if: <condition that would warrant revisiting, if any>
---
```
