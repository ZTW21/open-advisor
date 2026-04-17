# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/); version numbers follow [SemVer](https://semver.org/).

## [1.0.0] — 2026-04-17

First public release.

### The shape of the thing

- **Markdown-for-narrative + SQLite-for-numbers architecture.** Narrative files live at the repo root (`CLAUDE.md`, `STRATEGY.md`, `profile.md`, `principles.md`, `rules.md`, `goals.md`). Numeric truth lives in a local SQLite database the AI is not allowed to touch directly. Deterministic Python CLI (`finance ...`) owns all arithmetic and emits JSON the AI narrates.
- **Eight inviolable rules** codified in `CLAUDE.md`: no trades / transfers / payments, no specific tickers, no computing numbers from context, no credentials or SSN or full account numbers written to any file, no DB writes without dry-run + confirmation, explicit stale-data flagging, licensed-professional referral for estate / complex tax / divorce / bankruptcy, and triage-before-planning for users in distress.
- **Local-first by design.** No telemetry, no cloud sync, no hosted accounts. Your directory, your machine. `PRIVACY.md` has the full statement.

### CLI surface

Single entry point: `finance`. Every subcommand accepts root-level `--json` (`finance --json <command>`) for machine-readable output the AI consumes.

- **Core data:** `init`, `import` (dry-run default, `--commit` to write), `categorize`, `reconcile`, `rollback`, `export`, `backup`.
- **Account & cashflow queries:** `net-worth`, `cashflow`, `balance`, `account`, `fees`, `debts`.
- **Advisory flows:** `afford`, `rebalance`, `payoff`, `automation`, `tax-pack`, `windfall`.
- **Posture detection:** `mode` returns `debt` / `invest` / `balanced` based on live DB state; `HIGH_APR_THRESHOLD = 8.0`, mortgages excluded.
- **Reports:** `report daily`, `report weekly`, `report monthly`, `report quarterly`, `report annual`.
- **Sync:** `sync` with a pluggable adapter registry. Built-in adapters: `csv_inbox` (default, no-network inventory of `transactions/inbox/`); `simplefin` and `plaid` network-adapter scaffolds with a stable `SyncAdapter` contract returning structured `not_configured` / `not_implemented` errors until client code ships.
- Every write path creates a timestamped DB backup in `data/backups/` first. `finance rollback <batch_id>` reverses an import.

### Memory system

Six-type, always-indexed memory layer in `memory/`: facts, preferences, feedback, patterns, decisions, watchlist. `memory/MEMORY.md` is the always-loaded index (soft cap 50 lines). Quarterly `consolidate-memory` pass merges duplicates and prunes stale entries.

### STRATEGY.md — the advisor's brain

Living master plan with Long arc / Next 12 months / Next 90 days / Next 30 days / Dependencies / Open questions / Open gaps / "What I'm not doing" / History. Rewritten (not appended) on monthly, quarterly, annual, and life-event routines. All rewrite mechanics centralized in `routines/strategy-refresh.md` so cadence routines delegate rather than duplicate.

### Routines

Routines covering every recurring or on-demand flow: onboarding, daily, weekly, monthly, quarterly, annual, import, life-event, temptation-check, windfall, rebalance, automation-audit, mode-detect, rules-enforcement, loss-aversion, afford, debt-payoff, schedule, strategy-refresh.

### Scheduling

Seven scheduled jobs wired via the `schedule` skill during onboarding, all in local timezone: daily brief (08:00), weekly brief (Sunday 18:00), monthly report (1st of month 09:00), quarterly review (5th of Jan/Apr/Jul/Oct 09:00), annual review (Dec 15 09:00), automation audit (semiannual Apr/Oct 1st 10:00), nightly sync (03:00). Full spec in `routines/schedule.md`.

### Documentation & release

- `README.md` — quickstart, architecture diagram, daily usage, privacy summary.
- `CLAUDE.md` — system prompt for the AI: routing table, inviolable rules, voice, stated-rules enforcement.
- `CONTRIBUTING.md` — six design invariants that cannot be broken; step-by-steps for adding a CLI command, sync adapter, or routine.
- `PRIVACY.md` — what stays local, what the advisor refuses to write to disk, network behavior, sharing deliberately.
- `examples/example-user/` — fictional fully-populated "Alex Morgan" directory as a reference for what a real advisor directory looks like after months of use. Includes populated `memory/`, `state/`, `accounts/`, `STRATEGY.md`, sample daily / weekly / monthly reports, and a full decision journal entry.
- MIT license.

### Test coverage

178 tests, zero failures. Dependency-free harness pattern in `tests/test_sync.py` for environments without pytest.

### Known deferred work

- Multi-household / partner finances.
- Non-US tax regimes and retirement account types.
- Investment holdings snapshots (brokerage positions beyond cash balances).
- Network client code for the SimpleFIN and Plaid sync adapters.

These are good first issues — the contracts are stable.
