# Example populated directory — "Alex Morgan"

This is a fictional user's finance directory, populated enough to illustrate what a real post-onboarding setup looks like. All names, balances, employers, and amounts are made up. Nothing here is prescriptive.

**Do not copy this directory as your starting point.** Run `routines/onboarding.md` yourself — your answers will differ on every meaningful axis.

## The fictional user

- **Alex Morgan**, 34, single, lives in Austin TX.
- Software engineer, W-2, ~$135k gross + occasional small consulting income.
- Five accounts: one checking, one high-yield savings, one Roth IRA, one 401(k), one credit card carrying a modest balance.
- Currently in **balanced mode**: some credit card debt but not high-APR, emergency fund a little light, allocation targets are set.

## What's populated

- `profile.md`, `goals.md`, `rules.md`, `principles.md`, `STRATEGY.md` — the narrative spine.
- `state/income.md`, `state/debts.md`, `state/net-worth.md` — hand-maintained state snapshots with stale-by dates.
- `accounts/*.md` — one markdown file per account with narrative + metadata. Balances live in the DB, not here.
- `memory/MEMORY.md` and a handful of entries in `memory/facts/`, `memory/preferences/`, `memory/feedback/`, `memory/patterns/`.
- A sample daily brief, weekly summary, and monthly report in `reports/`.
- A sample decision journal entry in `decisions/`.

## What's not populated

- No SQLite database, no JSON exports, no transaction history. The fictional narrative implies transactions exist, but the example doesn't ship them — generating realistic ones would bloat the repo and could be mistaken for a template.
- No `CLAUDE.md` copy — use the framework's top-level `CLAUDE.md` as-is.

## Useful things to poke at

- **Compare** the populated `profile.md` here with the blank template at the repo root. Same frontmatter, filled-in fields.
- **Read** `memory/MEMORY.md` and follow a few links to see how the index points to individual memories.
- **Look at** `STRATEGY.md` to see the expected Long arc / Next 12 months / Next 30 days structure.
- **Compare** the sample daily brief (one sentence) with the weekly (~150 words) with the monthly (one page). That gradient is on purpose.

## License

Same MIT license as the rest of the project. The fictional data is public domain — reuse it in your own docs, demos, or tests.
