"""`finance sync` — pull statements into transactions/inbox/.

What it does:

  - With no args or `--list`: enumerates registered adapters and what
    they do. Always safe to run.
  - With `--adapter <name> --list-accounts`: asks the adapter what
    accounts it can see (for mapping to local accounts).
  - With `--adapter <name>`: runs `fetch_since` and drops files in
    `transactions/inbox/`. Does NOT import — the user still runs
    `finance import` (or a scheduled routine does).

Why sync and import are separate: adapters write files; the importer
parses + normalizes + dedupes + asks for confirmation. Keeping them
separate means a scheduled `finance sync` is safe (only creates files)
while the import step retains its dry-run confirmation invariant.

Error codes surfaced via emit_error:
  - unknown_adapter: --adapter name not in the registry
  - bad_since:       --since is not a valid YYYY-MM-DD date
  - sync_failed:     adapter raised SyncError; details.code carries the
                     adapter's error code (not_configured, auth_failed, ...)
"""

from __future__ import annotations

from datetime import date, timedelta

import click

from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.output import emit, emit_error
from finance_advisor.sync import SyncError, get_adapter, list_adapters


# Default lookback when --since isn't given. 35 days covers "last month
# plus a few spare days" which matches how most users think about
# statement cycles.
_DEFAULT_LOOKBACK_DAYS = 35


@click.command("sync")
@click.option(
    "--adapter",
    "adapter_name",
    default=None,
    help="Adapter to run (e.g. csv_inbox, simplefin, plaid). "
         "Omit to list available adapters.",
)
@click.option(
    "--list",
    "list_only",
    is_flag=True,
    default=False,
    help="List registered adapters and their descriptions.",
)
@click.option(
    "--list-accounts",
    "list_accounts",
    is_flag=True,
    default=False,
    help="Ask the adapter what remote accounts it can see.",
)
@click.option(
    "--since",
    "since",
    default=None,
    help="Fetch transactions since this date (YYYY-MM-DD). "
         f"Default: {_DEFAULT_LOOKBACK_DAYS} days ago.",
)
@click.option(
    "--account",
    "account_ids",
    multiple=True,
    help="Restrict to one or more remote account IDs. Repeatable.",
)
@click.pass_context
def sync(
    ctx: click.Context,
    adapter_name: str | None,
    list_only: bool,
    list_accounts: bool,
    since: str | None,
    account_ids: tuple[str, ...],
) -> None:
    """Pull statements from a sync adapter into transactions/inbox/.

    The default adapter is `csv_inbox`, which is a no-op inventory of
    existing files — safe to run with no configuration.
    """
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    # --list / no adapter → enumerate registered adapters.
    if list_only or adapter_name is None:
        payload = {
            "ok": True,
            "adapters": list_adapters(),
            "default": "csv_inbox",
        }

        def _render_list(p: dict) -> None:
            click.echo("Available sync adapters:")
            for a in p["adapters"]:
                marker = "  (default)" if a["name"] == p["default"] else ""
                click.echo(f"  {a['name']}{marker}")
                if a["description"]:
                    click.echo(f"      {a['description']}")

        emit(ctx, payload, _render_list)
        return

    # Resolve the adapter class.
    try:
        adapter_cls = get_adapter(adapter_name)
    except KeyError as exc:
        emit_error(
            ctx,
            str(exc),
            code="unknown_adapter",
            details={"requested": adapter_name},
        )
        return

    adapter = adapter_cls(config.finance_dir)

    # --list-accounts → ask, don't fetch.
    if list_accounts:
        try:
            accounts = adapter.list_accounts()
        except SyncError as exc:
            emit_error(
                ctx,
                exc.message,
                code="sync_failed",
                details={"adapter": adapter_name, "code": exc.code},
            )
            return

        payload = {
            "ok": True,
            "adapter": adapter_name,
            "accounts": [
                {
                    "remote_id": a.remote_id,
                    "name": a.name,
                    "institution": a.institution,
                    "type": a.type,
                    "currency": a.currency,
                }
                for a in accounts
            ],
        }

        def _render_accounts(p: dict) -> None:
            click.echo(f"Remote accounts from {p['adapter']}:")
            if not p["accounts"]:
                click.echo("  (none)")
                return
            for a in p["accounts"]:
                click.echo(
                    f"  {a['remote_id']}  {a['name']}  "
                    f"[{a['institution']} / {a['type']}]"
                )

        emit(ctx, payload, _render_accounts)
        return

    # Parse --since or default.
    if since is None:
        since_date = date.today() - timedelta(days=_DEFAULT_LOOKBACK_DAYS)
    else:
        try:
            since_date = date.fromisoformat(since)
        except ValueError:
            emit_error(ctx, f"Invalid --since: {since!r}", code="bad_since")
            return

    # Run the fetch.
    try:
        result = adapter.fetch_since(
            since_date,
            account_ids=list(account_ids) or None,
        )
    except SyncError as exc:
        emit_error(
            ctx,
            exc.message,
            code="sync_failed",
            details={"adapter": adapter_name, "code": exc.code},
        )
        return

    payload = {
        "ok": True,
        "since": since_date.isoformat(),
        **result.to_payload(),
    }

    def _render_fetch(p: dict) -> None:
        click.echo(f"Sync: {p['adapter']} (since {p['since']})")
        click.echo(f"  files in inbox: {len(p['files_written'])}")
        for f in p["files_written"]:
            click.echo(f"    - {f}")
        if p["skipped"]:
            click.echo(f"  skipped: {len(p['skipped'])}")
            for s in p["skipped"]:
                click.echo(f"    - {s.get('reason')}: {s.get('detail', '')}")
        if p["errors"]:
            click.echo(f"  errors: {len(p['errors'])}")
            for e in p["errors"]:
                click.echo(f"    - {e}")
        click.echo("")
        click.echo("  Next: run `finance import <file> --account <local_name>` "
                   "for each file above (then --commit).")

    emit(ctx, payload, _render_fetch)
