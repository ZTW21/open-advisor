---
name: Decisions Folder Guide (top-level)
description: Journal of meaningful moves as they happen. Different from memory/decisions/ which compresses the why for long-term reference.
type: folder-readme
---

# Decisions — journal of what and why

A dated journal of meaningful financial actions. Written at the time of the decision so the reasoning is fresh.

## Naming convention

`YYYY-MM-DD-<slug>.md`

Examples:
- `2026-02-03-refi-mortgage.md`
- `2026-03-20-roth-conversion.md`
- `2026-04-10-cancelled-gym.md`
- `2026-05-15-bonus-allocation.md`

## Frontmatter template

```yaml
---
name: <decision>
description: <one-line summary>
type: decision
decided_on: <ISO date>
stakes: <low | medium | high>
related:
  - <relevant files>
---
```

## Body structure (suggested)

- **Decision** — what, in one sentence
- **Context** — what was going on that led to this
- **Options considered** — alternatives and why they lost
- **Reasoning** — why this choice; what the user and advisor weighed
- **Expected outcome** — what you expect to happen
- **Review trigger** — when to revisit (date or condition)

## vs. `memory/decisions/`

- `decisions/` (this folder) = the full journal entry at the time.
- `memory/decisions/` = a compressed summary for long-term reference — the "why" that should never be re-litigated.

A major decision often generates both: a full entry here, and a compressed version in memory.
