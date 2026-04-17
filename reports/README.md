---
name: Reports Folder Guide
description: Generated outputs live here. Dated. Not loaded into context by default.
type: folder-readme
---

# Reports — generated outputs

Reports are written by routines. Don't edit them by hand — re-run the routine if something's wrong.

## Naming convention

- Daily: `YYYY-MM-DD-daily.md`
- Weekly: `YYYY-Www-weekly.md` (ISO week, e.g., `2026-w15-weekly.md`)
- Monthly: `YYYY-MM-monthly.md`
- Quarterly: `YYYY-Qn.md`
- Annual: `YYYY-annual.md`
- Ad-hoc: `YYYY-MM-DD-<slug>.md`

## Retention

Keep forever. Git history handles diff/evolution. Reports are cheap to keep and sometimes useful to look back on.

## Don't put non-report content here

Decisions go in top-level `decisions/`. Scenarios go in `scenarios/`. One-off analyses with a date in the name are fine here.
