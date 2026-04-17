---
name: Scheduling
description: How the advisor wires its routines into the `schedule` skill — which routines run when, at what local time, and how they connect to sync + reports.
type: routine
cadence: once at onboarding; reviewed annually
output_length: N/A (infrastructure routine)
updated: 2026-04-17
stale_after: 365d
related:
  - routines/daily.md
  - routines/weekly.md
  - routines/monthly.md
  - routines/quarterly.md
  - routines/annual.md
  - routines/automation-audit.md
  - routines/strategy-refresh.md
  - routines/import.md
sources:
  - finance_advisor/commands/sync.py
  - finance_advisor/sync/base.py
  - finance_advisor/sync/csv_inbox.py
  - finance_advisor/commands/report.py
---

# Scheduling

This routine lays out the **cron schedule** the advisor recommends at onboarding, the **prompts** each scheduled run uses, and how scheduled runs compose with the sync layer and the import pipeline. Everything here is declarative — the actual scheduling is done through the `schedule` skill (`create_scheduled_task` tool).

The `done-when` for Phase 12 is: **Sunday 6pm local produces a weekly brief without being asked.** This routine is how we get there.

## Design principles

1. **Observation is safe; writes require confirmation.** Scheduled routines may read the DB and write to `reports/`. They do NOT import transactions, modify accounts, categorize, or write to memory without the user's explicit green light on the next interactive turn. Imports still follow `routines/import.md`'s dry-run → confirm → `--commit` flow.

2. **Every job is idempotent.** Running the same routine twice in a day should produce the same artifact (or a dated second artifact with identical content). The user may re-run a missed job by hand.

3. **Local time wins.** The `schedule` skill evaluates cron in the user's local timezone — not UTC. Times below are local. If the user travels, we don't re-jigger the schedule.

4. **Fail open, flag loud.** A scheduled routine that can't run (stale data, missing CLAUDE.md, no inbox) should produce a short report that says so, not silently no-op.

## The schedule

| Task name | Cron (local) | Routine | What it does |
|---|---|---|---|
| `finance-daily-brief` | `0 8 * * *` | `routines/daily.md` | One-sentence brief for yesterday. Writes `reports/daily/YYYY-MM-DD.md`. |
| `finance-weekly-brief` | `0 18 * * 0` | `routines/weekly.md` | ~150-word summary for last week. Writes `reports/weekly/YYYY-Www.md`. **Phase 12's done-when target.** |
| `finance-monthly-report` | `0 9 1 * *` | `routines/monthly.md` | Full monthly report (~1 page). Also triggers the monthly `STRATEGY.md` rewrite (see `routines/strategy-refresh.md`). |
| `finance-quarterly-review` | `0 9 5 1,4,7,10 *` | `routines/quarterly.md` | Two-page quarterly review on the 5th of each quarter's first month. |
| `finance-annual-review` | `0 9 15 12 *` | `routines/annual.md` | Annual review on Dec 15 — year-end lookback + year-ahead shape. |
| `finance-automation-audit` | `0 10 1 4,10 *` | `routines/automation-audit.md` | Semiannual subscription audit (April 1 and October 1). |
| `finance-sync-nightly` | `0 3 * * *` | (this file, § Sync job) | Runs `finance sync --adapter <default>`. With `csv_inbox` this is a no-op inventory; with SimpleFIN/Plaid it fetches. Never imports. |

These cron expressions assume the user is okay with our defaults. At onboarding, offer to adjust (e.g., a night-owl user may want the daily at 11pm instead of 8am).

## The sync job

The nightly sync job is intentionally minimal:

```
finance --json sync --adapter <configured> --since <last_sync_or_35d_ago>
```

- With the default `csv_inbox` adapter this just inventories files the user dropped. Safe and silent.
- With `simplefin` / `plaid` (Phase 12.5), this fetches new transactions and writes files into `transactions/inbox/`.
- The job does NOT call `finance import`. Importing remains interactive because the import pipeline's dry-run + `--commit` step is a trust boundary (see CLAUDE.md §5 and `routines/import.md`). The weekly brief on Sunday will nudge the user to run import if inbox has new files.

If network sync fails, the job should write a short note to `reports/sync/YYYY-MM-DD.md` with the error code (`not_configured`, `auth_failed`, etc.) and move on. A broken sync should never break the daily/weekly schedule.

## Registering each job

For each row in the table above, call `create_scheduled_task` exactly once at onboarding. The prompt must be self-contained — future runs do NOT inherit this conversation's context.

### Template

```
create_scheduled_task(
  taskName="finance-weekly-brief",
  cronExpression="0 18 * * 0",
  prompt=<the self-contained prompt; see § Prompts>
)
```

### Prompts

Each scheduled run executes its own Claude session with the prompt below. Prompts must reference absolute paths, cite the relevant routine, and end with "do not mention this schedule unless the routine went sideways" — the user sees a report on disk, not a chat message.

#### finance-daily-brief

> You are the user's financial advisor, invoked by a scheduled job. Read `CLAUDE.md`, `memory/MEMORY.md`, and `routines/daily.md`. Execute the daily-brief routine end-to-end for yesterday's date. Write the output to `reports/daily/YYYY-MM-DD.md` (overwrite if present). Do not propose actions; the daily brief only observes. If data is stale (the CLI reports no transactions for the window), write a one-line note to that effect instead.

#### finance-weekly-brief

> You are the user's financial advisor, invoked by a scheduled job on Sunday evening. Read `CLAUDE.md`, `memory/MEMORY.md`, `STRATEGY.md` (only `§ Next 30 days`), and `routines/weekly.md`. Execute the weekly routine for the just-ending ISO week. Write the output to `reports/weekly/YYYY-Www.md` (overwrite if present). Run `finance --json anomalies --last 7d` and include any anomalies surfaced. Do not modify the DB. If `STRATEGY.md` is in template state (`version: 0.0`), skip the nudge and note that onboarding isn't complete.

#### finance-monthly-report

> You are the user's financial advisor, invoked on the 1st of the month. Read `CLAUDE.md`, `memory/MEMORY.md`, `STRATEGY.md`, and `routines/monthly.md`. Execute the monthly routine for the just-ending month. Write `reports/monthly/YYYY-MM.md`. Also perform the monthly `STRATEGY.md` rewrite per `routines/strategy-refresh.md` (scope: Next 30 days + Next 12 months sections; do NOT touch Long arc). Log any rule or memory updates to `memory/decisions/` as usual.

#### finance-quarterly-review

> You are the user's financial advisor, invoked on the 5th of the quarter's first month. Read `CLAUDE.md`, `memory/MEMORY.md`, `STRATEGY.md`, and `routines/quarterly.md`. Execute the quarterly routine for the just-ending quarter. Write `reports/quarterly/YYYY-Qn.md`. Run `finance --json report quarterly` and `finance --json rebalance` and cite both. Trigger the quarterly `STRATEGY.md` rewrite per `routines/strategy-refresh.md`.

#### finance-annual-review

> You are the user's financial advisor, invoked on December 15. Read `CLAUDE.md`, `memory/MEMORY.md`, `STRATEGY.md`, and `routines/annual.md`. Execute the annual routine for the current year. Write `reports/annual/YYYY.md`. Run `finance --json report annual` and `finance --json tax-pack --year YYYY` and cite both. Trigger the annual `STRATEGY.md` rewrite (all sections).

#### finance-automation-audit

> You are the user's financial advisor, invoked semiannually (April 1 and October 1). Read `CLAUDE.md`, `memory/MEMORY.md`, and `routines/automation-audit.md`. Run `finance --json automation --lookback-months 6` and execute the routine. Write `reports/automation/YYYY-MM.md`. The user will review the list interactively on the next turn; do not propose cancellations autonomously.

#### finance-sync-nightly

> You are the user's financial advisor, invoked nightly. Read `CLAUDE.md` briefly. Run `finance --json sync --adapter <configured_adapter>` with `--since` set to 35 days before today. If the result has `ok: true`, write a one-line note to `reports/sync/YYYY-MM-DD.md` summarizing `files_written` and `skipped` counts. If it has `ok: false`, write the error code and message to the same file and exit. Do NOT run `finance import`; that stays interactive.

## Onboarding integration

At onboarding (`routines/onboarding.md`), after the user confirms preferred times, call `create_scheduled_task` for each of the seven jobs. Save the task IDs to `state/schedule.md` (hand-maintained), so a future run can inspect or update them via `list_scheduled_tasks` / `update_scheduled_task`.

If the user declines scheduling, skip all calls but still produce `state/schedule.md` with a note explaining that the user runs routines on demand.

## Overrides and pauses

- **Travel / deep work blocks.** The user can pause individual jobs via `update_scheduled_task`. On return, re-enable; missed daily briefs are not re-generated retroactively.
- **Time change.** Local-tz cron handles DST automatically; no action needed.
- **New adapter.** If the user adds SimpleFIN or Plaid after onboarding, update `finance-sync-nightly`'s prompt to reference the new adapter name.

## What a scheduled run should NEVER do

- Modify account records or categorization rules.
- Commit imports (only dry-run preview at most).
- Write to `memory/preferences/` or `memory/feedback/` — memories are written from interactive conversations where consent is explicit.
- Rewrite `STRATEGY.md § Long arc` outside the annual cadence.
- Send notifications to external systems (email, SMS) — the artifact on disk is the contract.

## Testing

A manual smoke test:

1. `finance --json sync --adapter csv_inbox` → should complete with a clean payload.
2. `finance --json report weekly --week 2026-W15` → should print a full weekly payload.
3. The scheduled-task `list_scheduled_tasks` tool should show seven entries after onboarding.

Automated coverage lives in `tests/test_sync.py` (adapter plumbing) and the existing `tests/test_report_*.py` (routine outputs). There is no automated test for the cron wiring itself — that's a one-shot setup verified interactively at onboarding.
