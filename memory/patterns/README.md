---
name: Patterns Folder Guide
description: Guide for writing patterns/ memories. Not loaded into context by default.
type: folder-readme
---

# Patterns — what goes here

Behavioral or spending patterns the advisor has *observed* over time. Sourced from DB queries, not from user statements.

**Examples:**
- `groceries-trend.md` — "Grocery spend drifted from $650/mo in 2025 to $820/mo YTD 2026, mostly Whole Foods"
- `cc-always-paid-in-full.md` — "User has paid every credit card in full for 18 consecutive months — reliable"
- `q4-spending-spike.md` — "Discretionary spending jumps 35% in Nov-Dec each year"
- `subscription-creep.md` — "New recurring subscription added roughly every 6 weeks"

**What doesn't go here:** one-time events (those are `decisions/` if meaningful, or nothing), current balances (DB), stated preferences.

**When to write:** during daily/weekly/monthly routines, after running CLI queries. Cite the query and window.

**Frontmatter template:**
```yaml
---
name: <pattern name>
description: <one-line summary>
type: memory-pattern
written: <ISO date>
last_confirmed: <ISO date>
source_query: <the CLI command that produced this observation>
---
```

**Rewriting vs. appending:** rewrite patterns as they evolve. Git history keeps the prior versions. Retire patterns that no longer hold.
