---
name: Feedback Folder Guide
description: Guide for writing feedback/ memories. Not loaded into context by default.
type: folder-readme
---

# Feedback — what goes here

Corrections the user has given the advisor about how to behave. What to avoid. What to keep doing.

**Examples:**
- `stop-suggesting-cooking.md` — "User said 'don't suggest I cook more, I work 60hr/wk, meal prep is unrealistic' on 2026-03-02"
- `no-scolding-on-dining.md` — "User said 'stop harping on restaurant spending, we spend intentionally on this' on 2026-01-15"
- `shorter-weekly-briefs.md` — "User said weekly briefs are too long; keep under 100 words going forward"
- `keep-using-waterfall.md` — "User liked the waterfall breakdown in the March monthly; continue using"

Record from both corrections AND successes. Corrections prevent repeat mistakes; success memories prevent drift away from approaches the user liked.

**Structure:** lead with the rule, then a **Why:** line (the reason), and a **How to apply:** line (when it kicks in).

**Frontmatter template:**
```yaml
---
name: <feedback name>
description: <one-line summary>
type: memory-feedback
written: <ISO date>
last_confirmed: <ISO date>
---
```
