---
name: Preferences Folder Guide
description: Guide for writing preferences/ memories. Not loaded into context by default.
type: folder-readme
---

# Preferences — what goes here

Things the user has **explicitly stated** about how they want their money handled. Philosophy, not rules. These override the Boglehead default in `principles.md` when they conflict.

**Examples:**
- `prefers-debt-payoff.md` — "User said 'I hate having debt, I want it gone even if investing mathematically wins' on 2026-02-14"
- `dislikes-international.md` — "User prefers US-only equity, accepting concentration risk"
- `fidelity-for-life.md` — "Wants to consolidate at Fidelity; not interested in brokerage comparison shopping"
- `windfall-allocation.md` — "Any windfall: 50% to goals, 30% to taxable, 20% guilt-free spend"

**What doesn't go here:** hard rules (those go in `rules.md` — the user's own file), corrections (`feedback/`), observed behavior (`patterns/`).

**How they're used:** when the advisor's default advice would conflict with a preference, the preference wins and the advisor names it explicitly: "You told me you want debt gone first, so we're sticking with that even though the math would favor investing."

**Frontmatter template:**
```yaml
---
name: <preference name>
description: <one-line summary>
type: memory-preference
written: <ISO date>
last_confirmed: <ISO date>
stated_verbatim: <the user's actual words, in quotes>
---
```
