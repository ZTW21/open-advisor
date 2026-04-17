# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/); version numbers follow [SemVer](https://semver.org/).

## [1.1.0] — 2026-04-17

Pull-based cadence and an upgrade-safe layout. No data migration required — existing v1.0.0 installs pick this up with `git pull` and a re-run of `finance init`.

### Removed

- **Scheduled routines.** The seven cron jobs that ran on a clock (daily brief, weekly, monthly, quarterly, annual, automation audit, nightly sync) are gone. `routines/schedule.md` is deleted. Cadence reports now run when the user asks — every routine has an on-demand entry point.
- **The `schedule` skill dependency.** Onboarding no longer wires cron tasks. If the user wants a nudge, they can set a calendar reminder or put `finance report weekly` in a shell alias.

### Why

The scheduled-task architecture only fired when Cowork was open and the user's Mac was awake — missed windows were common, and users got silent gaps rather than briefs. Pull-based is simpler, more reliable, and matches how people actually use the advisor: they ask when they want to know.

### Added

- **Template hydration on `finance init`.** The init command now copies scaffolds from `templates/` into the user's directory — skipping anything that already exists. This is idempotent: first run hydrates, second run reports everything as skipped, and a new template added upstream is picked up on the next run without touching existing files.
- **`UPGRADING.md`.** The git-upstream-remote workflow for pulling framework releases without clobbering populated data, plus a rollback recipe.
- **Root-level `.gitignore` for user data.** `STRATEGY.md`, `profile.md`, `principles.md`, `rules.md`, `goals.md`, `state/*.md`, `memory/MEMORY.md`, per-category memory files, `accounts/*.md`, `decisions/*.md`, `scenarios/*.md`, and `reports/*` are excluded at the repo root. `README.md` (and `TEMPLATE.md` for accounts) are negation-pattern exempted so upstream can still ship instructions.
- **`state/README.md`.** Describes which files in `state/` are regenerated from the database and which are hand-maintained.

### Changed

- **Cadence routines** (`daily.md`, `weekly.md`, `monthly.md`, `quarterly.md`, `annual.md`, `automation-audit.md`, `onboarding.md`) — trigger blocks rewritten to describe the pull-based flow; any "scheduled: ..." lines removed.
- **`CLAUDE.md`** — scheduling routing row replaced with guidance that reports are pull-based; Rule 5 clarified so writes to `reports/` and `memory/` bypass dry-run but never bypass the reasoning step.
- **`README.md`** — onboarding path updated, "Cadence routines on demand" section added, pointer to `UPGRADING.md`.
- **`pyproject.toml`** — `templates/` directory included in the wheel build.

### Tests

185 passing (178 carried over from v1.0.0 + 7 new tests covering `finance init` hydration: noop when `templates/` missing, root + nested template copy, non-destructive behavior, idempotent re-run, picks up new templates after an upgrade, byte-for-byte preservation).

### Migration notes for v1.0.0 users

```bash
git remote add upstream https://github.com/<your-username>/open-advisor.git  # first time only
git fetch upstream
git merge upstream/main
bin/finance init    # hydrates any new templates; doesn't touch existing files
```

If you had the scheduled tasks wired via the `schedule` skill, they're orphaned now — `list_scheduled_tasks` will show them; remove with `update_scheduled_task` or just let them expire. The report commands they ran (`finance report daily`, etc.) still work exactly the same on demand.

---

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
