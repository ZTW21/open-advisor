"""`finance sync` — pull statements into transactions/inbox/.

What it does:

  - `finance sync` / `finance sync --list`: enumerate registered adapters.
  - `finance sync --adapter simplefin --list-accounts`: remote accounts.
  - `finance sync --adapter simplefin`: fetch since last pull, drop CSVs.
  - `finance sync setup-simplefin --token <base64>`: one-time token claim.
  - `finance sync map --remote-id <id> --account <name>`: link accounts.
  - `finance sync unmap --remote-id <id>`: unlink an account.
  - `finance sync status`: show mapping and last-sync state.

Why sync and import are separate: adapters write files; the importer
parses + normalizes + dedupes + asks for confirmation. The --auto-import
flag chains them but still respects dry-run by default.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import click

from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.output import emit, emit_error
from finance_advisor.sync import SyncError, get_adapter, list_adapters


_DEFAULT_LOOKBACK_DAYS = 35


@click.group("sync", invoke_without_command=True)
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
         "Default: since last sync, or 35 days ago.",
)
@click.option(
    "--account",
    "account_ids",
    multiple=True,
    help="Restrict to one or more remote account IDs. Repeatable.",
)
@click.option(
    "--auto-import",
    "auto_import",
    is_flag=True,
    default=False,
    help="After sync, run the import pipeline for each fetched file (dry-run).",
)
@click.option(
    "--commit",
    "commit",
    is_flag=True,
    default=False,
    help="With --auto-import: commit the imports (skip dry-run preview).",
)
@click.pass_context
def sync(
    ctx: click.Context,
    adapter_name: str | None,
    list_only: bool,
    list_accounts: bool,
    since: str | None,
    account_ids: tuple[str, ...],
    auto_import: bool,
    commit: bool,
) -> None:
    """Pull statements from a sync adapter into transactions/inbox/.

    The default adapter is `csv_inbox`, which is a no-op inventory of
    existing files — safe to run with no configuration.
    """
    # If a subcommand was invoked, let it handle everything.
    if ctx.invoked_subcommand is not None:
        return

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

        # Show mapping status if this is the simplefin adapter
        account_map = {}
        if hasattr(adapter, "_load_account_map"):
            account_map = adapter._load_account_map()

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
                    "mapped_to": account_map.get(a.remote_id),
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
                mapped = f" → {a['mapped_to']}" if a.get("mapped_to") else "  (unmapped)"
                click.echo(
                    f"  {a['remote_id']}  {a['name']}  "
                    f"[{a['institution']} / {a['type']}]{mapped}"
                )

        emit(ctx, payload, _render_accounts)
        return

    # Parse --since or smart default.
    if since is None:
        # Try to use last-synced date from adapter state
        smart_since = None
        if hasattr(adapter, "last_synced_since"):
            smart_since = adapter.last_synced_since()
        if smart_since:
            since_date = smart_since
        else:
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

    # Update balances from SimpleFIN response
    balance_updates = {}
    if hasattr(adapter, "get_balance_updates"):
        balance_updates = adapter.get_balance_updates()
        if balance_updates:
            _update_balances(config, balance_updates)

    payload = {
        "ok": True,
        "since": since_date.isoformat(),
        **result.to_payload(),
        "balances_updated": len(balance_updates),
    }

    if not auto_import:
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
            if p.get("balances_updated"):
                click.echo(f"  balances updated: {p['balances_updated']}")
            click.echo("")
            click.echo("  Next: run `finance import <file> --account <local_name>` "
                       "for each file above (then --commit).")

        emit(ctx, payload, _render_fetch)
        return

    # --auto-import: chain into the import pipeline
    _run_auto_import(ctx, config, adapter, result, commit=commit)


def _update_balances(config, balance_updates: dict[str, dict]) -> None:
    """Write balance updates from SimpleFIN to balance_history.

    Upserts: if a row for the same account+date already exists, update it.
    Source is tagged 'simplefin' so it's traceable.
    """
    from finance_advisor.db import connect, transaction

    from finance_advisor.analytics import LIABILITY_TYPES

    conn = connect(config.db_path)
    try:
        for local_name, info in balance_updates.items():
            acct = conn.execute(
                "SELECT id, account_type FROM accounts WHERE name = ?", (local_name,)
            ).fetchone()
            if not acct:
                continue

            as_of = info["as_of_date"]
            balance = info["balance"]

            # SimpleFIN reports credit card balances as negative (you owe = negative).
            # Our system stores liability balances as positive (amount owed).
            # Normalize: for liability accounts, use abs().
            if acct["account_type"] in LIABILITY_TYPES:
                balance = abs(balance)

            existing = conn.execute(
                "SELECT id FROM balance_history WHERE account_id = ? AND as_of_date = ?",
                (acct["id"], as_of),
            ).fetchone()

            with transaction(conn):
                if existing:
                    conn.execute(
                        "UPDATE balance_history SET balance = ?, source = ? WHERE id = ?",
                        (balance, "simplefin", existing["id"]),
                    )
                else:
                    conn.execute(
                        "INSERT INTO balance_history (account_id, as_of_date, balance, source) "
                        "VALUES (?, ?, ?, ?)",
                        (acct["id"], as_of, balance, "simplefin"),
                    )
    finally:
        conn.close()


def _run_auto_import(ctx, config, adapter, result, *, commit: bool) -> None:
    """Run the import pipeline for each synced file via CLI invocation."""
    from click.testing import CliRunner
    from finance_advisor.cli import cli as root_cli

    if not result.files_written:
        click.echo("Sync complete — no new files to import.")
        return

    runner = CliRunner()
    db_path = str(config.db_path)

    for file_path in result.files_written:
        filename = file_path.name
        # Parse local account name from filename: simplefin_<name>_<date>.csv
        parts = filename.split("_")
        if len(parts) >= 3 and parts[0] == "simplefin":
            local_name = "_".join(parts[1:-1])
        else:
            click.echo(f"  Skipping {filename} — cannot determine account name.")
            continue

        click.echo(f"\n--- Importing {filename} → account '{local_name}' ---")
        args = ["--db", db_path, "import", str(file_path), "--account", local_name]
        if commit:
            args.append("--commit")
        inv_result = runner.invoke(root_cli, args, catch_exceptions=False)
        click.echo(inv_result.output)

    if not commit:
        click.echo("Dry-run complete. Re-run with --auto-import --commit to write to the DB.")


# ---- subcommands ----


@sync.command("setup-simplefin")
@click.option("--token", required=True, help="Base64 setup token from SimpleFIN Bridge.")
@click.pass_context
def setup_simplefin(ctx: click.Context, token: str) -> None:
    """Claim a SimpleFIN setup token and store the access URL.

    Get a token at https://bridge.simplefin.org/simplefin/create
    """
    from finance_advisor.sync.simplefin_client import claim_token

    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    # Claim the token
    try:
        access_url = claim_token(token)
    except SyncError as exc:
        emit_error(ctx, exc.message, code=exc.code)
        return

    # Store the access URL
    secrets_dir = config.finance_dir / "data" / "secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)
    token_path = secrets_dir / "simplefin.token"
    token_path.write_text(access_url + "\n")
    os.chmod(token_path, 0o600)

    payload = {
        "ok": True,
        "message": "SimpleFIN configured.",
        "token_path": str(token_path),
    }

    def _render(p: dict) -> None:
        click.echo("SimpleFIN configured successfully.")
        click.echo(f"  Access URL stored in: {p['token_path']}")
        click.echo("")
        click.echo("Next steps:")
        click.echo("  1. finance sync --adapter simplefin --list-accounts")
        click.echo("  2. finance sync map --remote-id <id> --account <local_name>")
        click.echo("  3. finance sync --adapter simplefin")

    emit(ctx, payload, _render)


@sync.command("map")
@click.option("--remote-id", required=True, help="Remote account ID from SimpleFIN.")
@click.option("--account", "local_name", required=True,
              help="Local account name (must exist in the DB).")
@click.pass_context
def map_account(ctx: click.Context, remote_id: str, local_name: str) -> None:
    """Map a remote SimpleFIN account to a local account."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    # Verify the local account exists
    from finance_advisor.db import connect
    conn = connect(config.db_path)
    try:
        row = conn.execute(
            "SELECT id, name FROM accounts WHERE name = ?", (local_name,)
        ).fetchone()
    finally:
        conn.close()

    if not row:
        emit_error(
            ctx,
            f"No local account named '{local_name}'. "
            f"Create it first with: finance account add --name {local_name} ...",
            code="account_not_found",
        )
        return

    # Load and update the account map
    from finance_advisor.sync.simplefin_stub import SimpleFinAdapter
    adapter = SimpleFinAdapter(config.finance_dir)
    mapping = adapter._load_account_map()
    mapping[remote_id] = local_name
    adapter._save_account_map(mapping)

    payload = {
        "ok": True,
        "remote_id": remote_id,
        "local_account": local_name,
        "total_mapped": len(mapping),
    }

    def _render(p: dict) -> None:
        click.echo(f"Mapped: {p['remote_id']} → {p['local_account']}")
        click.echo(f"  {p['total_mapped']} account(s) mapped total.")

    emit(ctx, payload, _render)


@sync.command("unmap")
@click.option("--remote-id", required=True, help="Remote account ID to unmap.")
@click.pass_context
def unmap_account(ctx: click.Context, remote_id: str) -> None:
    """Remove a remote-to-local account mapping."""
    config = resolve_config(ctx.obj.get("db_override"))

    from finance_advisor.sync.simplefin_stub import SimpleFinAdapter
    adapter = SimpleFinAdapter(config.finance_dir)
    mapping = adapter._load_account_map()

    if remote_id not in mapping:
        emit_error(
            ctx,
            f"No mapping for remote ID '{remote_id}'.",
            code="not_mapped",
        )
        return

    removed_name = mapping.pop(remote_id)
    adapter._save_account_map(mapping)

    payload = {
        "ok": True,
        "remote_id": remote_id,
        "removed_account": removed_name,
        "total_mapped": len(mapping),
    }

    def _render(p: dict) -> None:
        click.echo(f"Unmapped: {p['remote_id']} (was → {p['removed_account']})")

    emit(ctx, payload, _render)


@sync.command("status")
@click.pass_context
def sync_status(ctx: click.Context) -> None:
    """Show SimpleFIN configuration, mapped accounts, and last sync times."""
    config = resolve_config(ctx.obj.get("db_override"))

    from finance_advisor.sync.simplefin_stub import SimpleFinAdapter
    adapter = SimpleFinAdapter(config.finance_dir)

    token_exists = adapter.token_path.exists()
    mapping = adapter._load_account_map()
    state = adapter._load_state()

    accounts_status = []
    for remote_id, local_name in mapping.items():
        last_synced = state.get(remote_id)
        accounts_status.append({
            "remote_id": remote_id,
            "local_account": local_name,
            "last_synced": last_synced,
        })

    payload = {
        "ok": True,
        "simplefin_configured": token_exists,
        "token_path": str(adapter.token_path),
        "mapped_accounts": accounts_status,
        "total_mapped": len(mapping),
    }

    def _render(p: dict) -> None:
        if p["simplefin_configured"]:
            click.echo("SimpleFIN: configured")
        else:
            click.echo("SimpleFIN: not configured")
            click.echo("  Run: finance sync setup-simplefin --token <token>")
            return

        if not p["mapped_accounts"]:
            click.echo("  No accounts mapped.")
            click.echo("  Run: finance sync --adapter simplefin --list-accounts")
            return

        click.echo(f"  {p['total_mapped']} account(s) mapped:")
        for a in p["mapped_accounts"]:
            synced = a["last_synced"] or "never"
            click.echo(f"    {a['remote_id']} → {a['local_account']}  (last sync: {synced})")

    emit(ctx, payload, _render)
