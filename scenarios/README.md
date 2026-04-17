---
name: Scenarios Folder Guide
description: What-if analyses. Exploratory projections.
type: folder-readme
---

# Scenarios — what-if analyses

Projections that help the user think about possible futures. Kept separate from the actual plan (`STRATEGY.md`) so they don't get confused.

## Examples

- `fi-2045.md` — what does financial independence by 2045 require?
- `house-upgrade-2028.md` — can we afford the next house in 2 years?
- `job-loss-resilience.md` — if the user loses their job, how long can they coast?
- `college-funding-2035.md` — projections for kids' college

## Filename convention

`<topic>-<target-date-or-context>.md`

## Frontmatter template

```yaml
---
name: <scenario>
description: <one-line question being explored>
type: scenario
assumptions:
  - <key assumptions the scenario depends on>
built_on: <ISO date>
stale_after: 180d
---
```

## Body structure

- **Question** — what you're exploring, in one sentence
- **Assumptions** — the numbers driving the projection (be explicit)
- **Projection** — year-by-year or milestone-by-milestone
- **Sensitivities** — what happens if key assumptions change
- **Implications** — what this means for `STRATEGY.md`
- **Decision if any** — if this leads to an action, link to the decisions entry

## Don't let scenarios rot

Scenarios become stale when assumptions drift. Re-run annually or when reality clearly diverges from what was assumed.
