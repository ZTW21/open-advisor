---
name: Daily Brief
description: How the advisor produces the one-sentence daily brief — source it from the CLI, never from context, and write it to reports/.
type: routine
cadence: daily (morning)
output_length: one sentence
updated: 2026-04-17
stale_after: never
related:
  - reports/
  - routines/weekly.md
sources:
  - finance_advisor/commands/report.py
  - finance_advisor/commands/anomalies.py
  - finance_advisor/analytics.py
---

# Daily Brief

Every morning you (the advisor) produce a single-sentence summary of yesterday. This is the lightest possible touchpoint — the goal is *one line* that the user can read in 10 seconds and move on, unless something genuinely needs attention.

## Trigger

- Scheduled: every morning at 8am local (`0 8 * * *`), wired via `routines/schedule.md` as the `finance-daily-brief` task.
- On demand: user says "what happened yesterday" or "give me the daily."

## Flow

### 1. Pull the payload

```
finance --json report daily
```

This returns totals for yesterday, the top merchants, anomalies detected for the day, and a `suggested_sentence` fallback. You do not compute any of this yourself — CLAUDE.md §3.

### 2. Compose the sentence

Use the payload to write *one* sentence. Never more. Pick the angle based on what the payload shows:

- **Quiet day (no anomalies, low count):** lead with net cashflow.
  > "Yesterday: net +$42 across 3 routine charges."

- **Anomaly present:** lead with the anomaly.
  > "Heads up: $180 at LA Fitness yesterday — first time over $50 there."

- **No activity:** say so.
  > "No activity yesterday."

### 3. (Optional) Persist the brief

If the user asks you to save it, or if this is a scheduled run:

```
finance --json report daily --write
```

`--write` saves a short markdown file at `reports/YYYY-MM-DD-daily.md`. The CLI writes a default sentence; if you composed a better one, say so when delivering the brief and note that the canonical copy is the advisor's voice, not the CLI fallback.

### 4. Link into memory, if relevant

If the day surfaced a **pattern** (third time dining over $80 this week, a new merchant that looks recurring, a bill that came earlier than usual), write a short `memory/patterns/<slug>.md` entry and add the one-liner to `memory/MEMORY.md`. Don't write a pattern memory for single occurrences — patterns require repetition or trend.

## Content rules

- One sentence. If you need more, save it for the weekly.
- No lists in a daily.
- Cite the source: the daily brief is always rooted in `finance report daily --json` (or `finance anomalies --since yesterday`).
- Never speculate. "Unusual charge" → only if the detector flagged it, not vibes.
- Don't ask open-ended questions in the daily. The user is skimming. If they want to dig in, they'll say so.

## Voice examples

- "On track — $47 under weekly pace."
- "Heads up: $210 at Costco yesterday (3.5x typical) — intentional?"
- "Quiet day — payroll hit on schedule."
- "No activity — worth double-checking the Chase sync hasn't gotten stuck."

## Safety

- **Don't compute totals yourself.** Read them from the payload.
- **Don't flag things the CLI didn't flag.** If you *feel* something's unusual but the detectors didn't catch it, mention it in the weekly, not the daily.
- **Never recommend a trade or transfer from a daily.** Dailies observe; weeklies advise.

## What the daily brief is NOT

- Not a task list.
- Not a budget update — that's weekly and monthly.
- Not a place for strategy changes.
- Not where we give opinions on individual securities.

## Useful sub-commands

| Task | Command |
|---|---|
| Yesterday payload | `finance --json report daily` |
| Specific date | `finance --json report daily --date YYYY-MM-DD` |
| Save to reports/ | `finance --json report daily --write` |
| Anomalies only | `finance --json anomalies --since yesterday` |
