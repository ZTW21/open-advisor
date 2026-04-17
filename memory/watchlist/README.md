---
name: Watchlist Folder Guide
description: Guide for writing watchlist/ memories. Time-sensitive. Not loaded into context by default.
type: folder-readme
---

# Watchlist — what goes here

Things to keep an eye on. Time-sensitive. Expires when acted on.

**Examples:**
- `netflix-cancellation.md` — "User mentioned wanting to cancel Netflix on 2026-03-20 but hasn't; bring up in next weekly brief"
- `upcoming-bonus-2026-q2.md` — "Bonus expected around 2026-05-15; apply windfall protocol"
- `cd-maturity-2026-06.md` — "CD matures 2026-06-15; decide whether to roll or redirect"
- `tax-extension-decision.md` — "User is deciding whether to file extension; they said they'd decide by end of March"

**Lifecycle:** write when the item surfaces. Surface in the next appropriate routine. **Delete** (or move to `decisions/` with resolution) once acted on. Don't let watchlist items accumulate indefinitely.

**Frontmatter template:**
```yaml
---
name: <watch item>
description: <one-line summary>
type: memory-watchlist
written: <ISO date>
surface_by: <ISO date when this should be raised>
expires: <ISO date when this becomes moot if not acted on>
---
```
