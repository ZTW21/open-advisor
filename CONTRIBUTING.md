# Contributing

Thanks for your interest. This project is deliberately small and opinionated. Contributions that preserve both properties are very welcome.

## Design invariants — please don't break these

A PR that violates any of the following will not land without a deep conversation first:

1. **The AI never does arithmetic on money.** Every number surfaced to the user traces to a CLI command that produced it. Don't add advisory code paths that estimate, approximate, or interpolate financial figures in prose.
2. **No trades, transfers, or payments.** The CLI has no execute-side endpoints and won't grow any. Sync adapters are read-only.
3. **Database writes follow dry-run → confirm → commit.** The only exception is scheduled routines that write to `reports/`. If you add a new write path, it needs a `--commit` gate and a preview.
4. **Specificity rule.** Advise at the category/allocation level, not the security level. Code that recommends specific tickers or timing is out of scope.
5. **Local-first.** The CLI has no outbound network calls outside the sync-adapter layer. Telemetry is a non-starter.
6. **Cite or it didn't happen.** Numbers and recommendations trace to files or CLI output.

Details are in `CLAUDE.md § The inviolable rules`.

## Repo layout

```
src/finance_advisor/
  cli.py                   Click root group
  commands/                One file per subcommand (finance <cmd>)
  sync/                    Pluggable sync adapters
  importers/               CSV/OFX parsers
  migrations/              SQLite migrations (numbered)
  analytics.py             Pure functions over the DB
  categorize_engine.py     Rule-based categorization
  normalize.py             Merchant name normalization
  db.py                    Connection + migration runner
  config.py                Path resolution (find_finance_dir, ...)
  output.py                emit() / emit_error() — the --json surface

tests/                     One file per subcommand; conftest.py has fixtures
routines/                  Markdown specs for AI-driven routines
bin/finance                Thin wrapper — just runs python -m finance_advisor
```

## Adding a new CLI command

Most CLI commands are ~80–200 lines. The pattern:

1. Create `src/finance_advisor/commands/<name>.py`. Define a Click command. Use `resolve_config(ctx.obj.get("db_override"))` to find the finance directory. Emit results via `output.emit(ctx, payload, human_renderer)` — the `--json` flag is handled globally at the root group.
2. Errors go through `output.emit_error(ctx, message, code="stable_error_code")`. Error codes are part of the public surface; keep them stable.
3. Register in `src/finance_advisor/cli.py`.
4. Write tests in `tests/test_<name>.py` using the existing `invoke` / `finance_dir` / `runner` fixtures from `conftest.py`.
5. If the command corresponds to an advisor workflow, add a routine in `routines/<name>.md` and link it from the routing table in `CLAUDE.md`.

Example to crib from: `src/finance_advisor/commands/mode.py` (small) or `payoff.py` (larger).

## Adding a new sync adapter

Implement `SyncAdapter` from `src/finance_advisor/sync/base.py`. Required methods:

- `list_accounts() -> list[RemoteAccount]`
- `fetch_since(since: date, *, account_ids=None) -> SyncResult`

An adapter **must not** write to the database directly. It writes files into `transactions/inbox/`; the import pipeline handles the rest. Register via `register("<name>", MyAdapter)`.

## Adding a routine

A routine is a markdown file in `routines/` with YAML frontmatter (name, description, cadence, sources, related). The file should be self-contained enough that an AI assistant could execute it cold, in a fresh session, given only `CLAUDE.md` + `memory/MEMORY.md` + the routine file itself. The "Flow" section names the exact CLI commands to run and cites the sources of every number.

Examples of well-shaped routines: `routines/afford.md`, `routines/loss-aversion.md`, `routines/rebalance.md`.

## Testing

```bash
pip install -e '.[dev]'
pytest -v
```

Tests use Click's `CliRunner` and a per-test tmp finance directory. There is no real bank, no real network, no fixtures that depend on wall-clock time — use `--as-of YYYY-MM-DD` for date-dependent assertions.

New CLI commands should cover:

- Happy path with `--json` — assert the payload shape.
- Each error code — assert `ok: False` and `error: <code>`.
- Help text — assert the command shows up in `finance --help` (useful smoke).

The project runs in environments without pytest installed via a fallback harness; avoid `pytest.raises` or `pytest.approx` in new tests where possible. See `tests/test_sync.py` for the dependency-free pattern.

## Commit style

- Present-tense, imperative: "Add foo", not "Added foo".
- One change per commit where reasonable. "Add `finance foo` command" and "Document `finance foo` in CLAUDE.md" are separate commits.

## Pull requests

- Link the issue the PR addresses (or open one first if no discussion exists).
- Note any new error codes, routines, or adapter names — these are user-facing contracts.
- If the PR touches `CLAUDE.md` or any `routines/*.md`, include a one-line note about how AI behavior changes.
- Keep the diff small. If you find yourself touching >10 files, that's usually two or more PRs.

## What we probably won't accept

- **A web UI.** The markdown-and-CLI surface is intentional. A UI belongs in a separate project that wraps this one.
- **Cloud sync, hosted accounts, telemetry.** See "Design invariants."
- **Security-specific recommendations.** See "Specificity rule."
- **Heavy dependencies.** The core CLI has one required dependency (`click`). Optional extras like `rich` and `ofxtools` are fine; adding another required dep needs a strong case.
- **Complex ML/LLM calls from inside the CLI.** The CLI is deterministic. The AI assistant is the one doing inference; the CLI just answers its questions.

## Questions

Open an issue. "Is this a good fit?" questions before starting a large PR are welcomed and usually save everyone time.
