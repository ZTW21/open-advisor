# Privacy Statement

This document explains what data this project touches, where it lives, and what we will and will not do with it.

## Short version

Everything stays on your machine by default. No telemetry. No analytics. No background network calls. No cloud. No account. Nothing leaves your computer unless **you** explicitly share it — with an AI assistant, a CPA, a partner, or a friend.

## What lives on your disk

A populated finance directory typically contains:

- **Markdown files** — profile, principles, rules, goals, strategy, account narratives, reports, memory, decisions. Human-readable. You can open them in any text editor.
- **A SQLite database** (`data/finance.sqlite`) — transactions, balances, categorization rules, scheduled activity. Local only. Readable with any SQLite client.
- **JSON exports** (`data/exports/`) — canonical snapshots regenerated from the database. Committed to git so history is diffable.
- **Dated backups** (`data/backups/`) — the database is copied here before any write that could mutate it. Git-ignored by default.
- **Statement files** (`transactions/inbox/`, `transactions/processed/`) — the raw CSV/OFX/QFX files you download from your bank. These contain merchant names, amounts, dates, and sometimes partial account numbers from your bank's export. Git-ignored by default.
- **Sync secrets** (`data/secrets/`) — if you configure a network sync adapter (SimpleFIN, Plaid), its access tokens live here at file mode `0600`. Git-ignored.

## What the advisor will never write to disk

Per the inviolable rules in `CLAUDE.md`:

- **Credentials** — bank passwords, login details, session tokens outside `data/secrets/`.
- **Full account numbers** — account narratives in `accounts/*.md` use the last 3–4 digits at most.
- **Social Security numbers** — even if you volunteer one, the advisor will decline to save it.

If any of the above ends up in a file because you typed it, the advisor should call it out and help you remove it.

## Network behavior

The CLI (`finance …`) is entirely offline. It reads and writes local files and the local SQLite database. It makes zero outbound network calls.

Network-capable components:

- **Sync adapter layer** (`src/finance_advisor/sync/`):
  - `csv_inbox` (default) — does not touch the network. It only inventories files you've dropped into `transactions/inbox/`.
  - `simplefin` — fetches transactions and balances from SimpleFIN Bridge using a user-held access token stored at `data/secrets/simplefin.token`. Read-only by design; SimpleFIN tokens cannot move money, change passwords, or access anything beyond transaction history. The only outbound calls go to `beta-bridge.simplefin.org`.
  - `plaid` (stubbed) — when implemented, will use Plaid Link. Credentials pass between you and Plaid; they never pass through our code.

  Sync adapters write CSV files to `transactions/inbox/`. The `--auto-import` flag chains into the import pipeline, but the same dedup and categorization rules apply regardless of source.

- **Web dashboard** (`finance dashboard`):
  - Runs a local HTTP server on `127.0.0.1:8765` (configurable). Read-only — it queries the same SQLite database the CLI uses.
  - Makes zero outbound network calls. All data stays on your machine.
  - Accessible only from localhost by default. Use `--host 0.0.0.0` only if you want LAN access (and understand the implications).

## The AI assistant

This framework is designed to be driven by an AI assistant (Claude and similar). The assistant reads your markdown files and queries the CLI. Whatever it reads becomes part of its context window for that session.

This means:

- The AI assistant provider you choose (e.g. Anthropic) sees whatever you share with the assistant during the conversation.
- The assistant provider's privacy policy governs how that data is handled on their end. **Review it before using.**
- You can choose to work entirely offline (no AI assistant, just the CLI) if you prefer. Every advisory routine has a CLI-only fallback; the assistant makes them easier, not mandatory.

We do not collect, proxy, or mediate any of this traffic. You're using the assistant's client directly; this project is a set of files in a directory it can read.

## Git and version control

The directory is designed to be git-tracked. By default, the following are **git-ignored** (see `.gitignore`):

- The SQLite database and its journals (working store is volatile; JSON exports are the canonical history).
- `data/backups/` (local DB snapshots).
- `data/secrets/` (tokens).
- `transactions/inbox/` and `transactions/processed/` (raw statement files — personal).
- Editor and OS cruft.

The following **are** tracked:

- All markdown (profile, goals, rules, principles, strategy, accounts, memory, reports, decisions).
- JSON exports (aggregated, categorized transaction history).
- The code under `src/`.

This means: if you push your repo to a remote, you're publishing your narrative, your memory, your reports, and your aggregated transaction history. If that's not what you want, keep the repo local, or push to a private remote.

We recommend: **do not push to a public remote** unless you have deliberately redacted everything personal (see `examples/example-user/` for a redacted template).

## Telemetry

None. The project does not phone home. It does not send usage metrics, crash reports, or "anonymous" analytics to anyone. The CLI has no network code outside the sync adapter layer described above.

If you ever see outbound network activity from `finance …` that isn't from a sync adapter you configured, that's a bug — please file an issue.

## Third-party services (optional)

If you choose to enable them:

- **SimpleFIN Bridge** — you register with them directly; you hold your own token. They see the transactions they fetch for you. This project does not proxy that traffic.
- **Plaid** — same pattern; credentials flow between you and Plaid; we see only the resulting tokens and transaction data you've authorized.
- **An AI assistant** — see above. Whatever you share in your assistant session is visible to the assistant provider.

None of these are required. The manual flow (download a CSV from your bank, drop it in `transactions/inbox/`, run `finance import`) works without any third party.

## Sharing deliberately

You may want to share specific outputs with:

- **A CPA.** The `finance tax-pack --year YYYY` command produces a clean tax-handoff payload. Share that file; don't share the raw DB.
- **A partner.** Share specific report files from `reports/`, not the whole directory.
- **A human advisor.** `STRATEGY.md` + relevant `state/*` + JSON exports give them the picture without exposing your full transaction history.

The project is structured so that you can share narrow outputs without sharing the underlying data.

## Reporting concerns

If you spot something that looks like a privacy regression (outbound network calls, unexpected file writes, secrets leaking to tracked files), please file an issue or open a PR. Privacy is a core design invariant of this project — bugs here are taken seriously.

## Disclaimer

This project is not legal, tax, or financial advice. It is a tool for organizing your own financial data. For questions about your legal or tax obligations regarding that data, consult a qualified professional.
