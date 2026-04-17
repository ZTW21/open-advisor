---
name: Facts Folder Guide
description: Guide for writing facts/ memories. Not loaded into context by default.
type: folder-readme
---

# Facts — what goes here

Discrete, rarely-changing facts about the user. One file per fact or tightly-related group.

**Examples:**
- `employer.md` — "Works at Acme since 2023, salary $X, options vest quarterly"
- `household.md` — "Married to Sam, 2 kids (Alex 8, Jordan 5), mortgage in OH"
- `health.md` — "Chronic condition affecting retirement planning horizon"
- `family-financial-help.md` — "Helps mother with $500/mo since 2024"

**What doesn't go here:** current balances (DB), philosophy (that's `preferences/`), corrections (that's `feedback/`).

**Frontmatter template:**
```yaml
---
name: <fact name>
description: <one-line summary>
type: memory-fact
written: <ISO date>
last_confirmed: <ISO date>
---
```

**Index entry format** (in `memory/MEMORY.md`):
```markdown
- [Fact title](facts/filename.md) — one-line hook
```

Update `last_confirmed` when you hear the fact reaffirmed. Retire facts that become stale.
