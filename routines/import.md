---
name: Import Routine
description: How the advisor walks the user through importing statements — dry-run, preview, confirm, commit, categorize, summarize. Never silent, never auto-commit.
type: routine
cadence: on demand (when files appear in transactions/inbox/)
output_length: short summary
updated: 2026-04-17
stale_after: never
related:
  - transactions/inbox/
  - transactions/processed/
  - transactions/rules.md
  - transactions/categories.md
sources:
  - finance_advisor/commands/import_.py
  - finance_advisor/commands/categorize.py
---

# Import Routine

This is how you (the advisor) bring new statements into the database. The CLI does all the parsing, deduping, categorizing, and transfer-pairing. Your job is to narrate, ask for confirmations, and help the user resolve anything the rules didn't cover.

## Trigger

- User says "sync my accounts" or "pull my transactions" → run the SimpleFIN sync path (see below).
- User drops files in `transactions/inbox/` and asks you to import → run the manual CSV path.
- You notice files in `inbox/` at the start of a routine (daily, weekly) — surface them but don't auto-import.

## SimpleFIN sync path (preferred for linked accounts)

For accounts connected via SimpleFIN (Chase, Ally, and any others mapped), use:

```
finance --json sync --adapter simplefin --auto-import --commit
```

This single command:
1. Pulls new transactions since the last sync for all mapped accounts.
2. Updates balances in `balance_history` from SimpleFIN's response.
3. Imports, deduplicates, categorizes, and commits the transactions.

Report the results to the user: new transactions per account, duplicates skipped, balances updated.

For accounts SimpleFIN can't reach (Apple Card, Bilt, etc.), fall back to the manual CSV flow below.

## Manual CSV path (fallback)

## Flow

### 1. Inventory

List what's in `transactions/inbox/`. For each file, identify or ask which account it belongs to. Don't guess from filenames — confirm with the user once per file. If the user hasn't told you, ask:

> "I see `chase_2026_q1.csv` and `amex_mar.csv` in your inbox. I'll map `chase_2026_q1.csv` to your `chase` account and `amex_mar.csv` to `cc_amex`. Sound right?"

### 2. Dry-run

For each file, run:

```
finance --json import <file> --account <name>
```

Dry-run is the default — **nothing is written yet.** Read the JSON payload.

### 3. Preview

Summarize the dry-run in plain text for the user. Pull numbers straight from the payload — never compute them yourself.

```
chase_2026_q1.csv → chase
  parsed: 247 rows
  new: 183   duplicates already in DB: 62   duplicates inside this file: 2
  will auto-categorize: 156   uncategorized: 27
```

If `uncategorized` is non-zero, name a few examples from the `preview` array so the user sees what's unresolved.

### 4. Confirm with the user

Ask explicitly:

> "Looks good? Want me to commit, or do you want to change anything first?"

Do not commit until the user says yes. This is a hard rule (CLAUDE.md §5).

### 5. Commit

For each file:

```
finance --json import <file> --account <name> --commit
```

Read back the `import_id`, `moved_to`, and `transfers_paired` counts.

### 6. Handle uncategorized

For each uncategorized transaction, either:

**(a) Assign a one-off category:**
```
finance --json categorize set --txn <id> --category <name>
```

**(b) Create a rule so future statements auto-categorize:**
```
finance --json categorize rule add --match "<substring>" --category <name>
```

Bias toward (b) when the merchant is recurring. Confirm the rule with the user before adding — rules silently shape future imports.

After adding new rules, you may re-run them over existing rows:

```
finance --json categorize run          # dry-run
finance --json categorize run --commit # apply
```

### 7. Sanity check

After committing, run `finance --json net-worth` to confirm the overall picture moved in the expected direction. If a single large transaction landed in the wrong account, this catches it.

### 8. Summarize

Give the user one short paragraph:

> "Imported 183 new transactions across 3 files. 156 auto-categorized, 27 needed review — we handled 18 and I added 4 new rules so next time is smoother. 1 transfer paired between chase and ally. Source files moved to `transactions/processed/2026/`."

## Safety

- **Never commit without explicit user confirmation.** Dry-run, preview, ask, commit.
- **Never parse files yourself.** The CLI does it. You read JSON.
- **Never compute totals from raw rows.** Use the `summary` payload.
- If the CLI errors (parse_error, account_not_found, etc.), stop and report. Don't try to "fix" by hand.

## What the advisor does NOT do

- Does not parse CSV or OFX files.
- Does not insert, update, or delete transactions directly in the DB.
- Does not guess which account a file belongs to.
- Does not silently add rules. Every new rule is confirmed.

## Useful sub-commands reference

| Task | Command |
|---|---|
| See inbox | `ls transactions/inbox/` |
| Dry-run import | `finance --json import <file> --account <name>` |
| Commit import | `finance --json import <file> --account <name> --commit` |
| List uncategorized | `finance --json categorize list` |
| Assign one txn | `finance --json categorize set --txn <id> --category <name>` |
| Add rule | `finance --json categorize rule add --match <pattern> --category <name>` |
| List rules | `finance --json categorize rule list` |
| Re-run rules | `finance --json categorize run --commit` |
