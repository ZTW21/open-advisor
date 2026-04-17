"""`finance balance` — record hand-entered balance snapshots.

The `balance_history` table is one row per (account, as-of-date). For credit
cards, loans, and mortgages, record the *outstanding amount owed* as a
positive number; the net-worth math flips the sign based on account type.

Idempotent on (account, as-of-date): calling `balance set` twice with the
same account and date updates the existing snapshot rather than duplicating.

Phase 4 success criterion: `finance init && account add && balance set &&
net-worth` returns a correct answer.
"""

from __future__ import annotations

import re
from datetime import date

import click

from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect, transaction
from finance_advisor.output import emit, emit_error


_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_as_of(value: str | None) -> str:
    """Return an ISO date string. `value` is either None (→ today) or YYYY-MM-DD."""
    if value is None:
        return date.today().isoformat()
    if not _ISO_DATE_RE.match(value):
        raise click.BadParameter(f"--as-of must be YYYY-MM-DD, got {value!r}")
    # Validate parse (raises ValueError on e.g. 2026-02-30)
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise click.BadParameter(f"--as-of is not a valid date: {exc}") from exc
    return value


@click.group("balance")
def balance() -> None:
    """Record and inspect balance snapshots."""


@balance.command("set")
@click.option("--account", required=True, help="Account nickname (see `finance account list`).")
@click.option(
    "--balance",
    "balance_value",
    required=True,
    type=float,
    help="Balance as a number. For liabilities, the positive amount owed.",
)
@click.option(
    "--as-of",
    default=None,
    help="Date this balance was true (YYYY-MM-DD). Default: today.",
)
@click.option(
    "--source",
    type=click.Choice(["manual", "import", "reconcile"]),
    default="manual",
    show_default=True,
    help="Where the balance came from.",
)
@click.option("--notes", default=None, help="Freeform note.")
@click.pass_context
def set_balance(
    ctx: click.Context,
    account: str,
    balance_value: float,
    as_of: str | None,
    source: str,
    notes: str | None,
) -> None:
    """Record or update a balance snapshot for an account on a given date."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    as_of_date = _parse_as_of(as_of)

    if balance_value < 0:
        click.echo(
            "Warning: --balance is negative. For liability accounts (credit_card, "
            "loan, mortgage) pass the positive amount owed — net-worth math flips "
            "the sign by account type.",
            err=True,
        )

    conn = connect(config.db_path)
    try:
        acct = conn.execute(
            "SELECT id, name, account_type FROM accounts WHERE name = ?", (account,)
        ).fetchone()
        if acct is None:
            emit_error(
                ctx,
                f"Account '{account}' not found.",
                code="account_not_found",
                details={"name": account},
            )
            return

        existing = conn.execute(
            "SELECT id, balance, source, notes FROM balance_history "
            "WHERE account_id = ? AND as_of_date = ?",
            (acct["id"], as_of_date),
        ).fetchone()

        with transaction(conn):
            if existing is not None:
                conn.execute(
                    "UPDATE balance_history SET balance = ?, source = ?, notes = ? "
                    "WHERE id = ?",
                    (balance_value, source, notes, existing["id"]),
                )
                action = "updated"
                previous = {"balance": existing["balance"], "source": existing["source"]}
            else:
                conn.execute(
                    "INSERT INTO balance_history (account_id, as_of_date, balance, source, notes) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (acct["id"], as_of_date, balance_value, source, notes),
                )
                action = "inserted"
                previous = None
    finally:
        conn.close()

    payload = {
        "ok": True,
        "action": action,
        "account": account,
        "account_type": acct["account_type"],
        "as_of_date": as_of_date,
        "balance": balance_value,
        "source": source,
        "notes": notes,
        "previous": previous,
    }

    def _render(p: dict) -> None:
        verb = "Updated" if p["action"] == "updated" else "Recorded"
        click.echo(
            f"{verb} balance for '{p['account']}' on {p['as_of_date']}: "
            f"${p['balance']:,.2f} ({p['source']})"
        )
        if p["previous"] is not None:
            click.echo(
                f"  Previous: ${p['previous']['balance']:,.2f} ({p['previous']['source']})"
            )

    emit(ctx, payload, _render)


@balance.command("list")
@click.option("--account", default=None, help="Filter to one account. Default: all.")
@click.option(
    "--since",
    default=None,
    help="Only show snapshots on/after this date (YYYY-MM-DD).",
)
@click.option(
    "--limit",
    default=None,
    type=int,
    help="Limit to the N most recent snapshots per account.",
)
@click.pass_context
def list_balances(
    ctx: click.Context,
    account: str | None,
    since: str | None,
    limit: int | None,
) -> None:
    """Show balance history — all accounts, or filter by --account."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    if since is not None and not _ISO_DATE_RE.match(since):
        raise click.BadParameter(f"--since must be YYYY-MM-DD, got {since!r}")

    conn = connect(config.db_path)
    try:
        params: list[object] = []
        where_bits: list[str] = []
        if account is not None:
            acct = conn.execute(
                "SELECT id FROM accounts WHERE name = ?", (account,)
            ).fetchone()
            if acct is None:
                emit_error(
                    ctx,
                    f"Account '{account}' not found.",
                    code="account_not_found",
                    details={"name": account},
                )
                return
            where_bits.append("bh.account_id = ?")
            params.append(acct["id"])
        if since is not None:
            where_bits.append("bh.as_of_date >= ?")
            params.append(since)

        where_clause = ""
        if where_bits:
            where_clause = " WHERE " + " AND ".join(where_bits)

        # If --limit is set, we want "N most recent per account". Use a window
        # via a correlated subquery. Without --limit we just sort globally.
        if limit is not None:
            query = (
                "SELECT a.name AS account, a.account_type, bh.as_of_date, "
                "bh.balance, bh.source, bh.notes "
                "FROM balance_history bh "
                "JOIN accounts a ON a.id = bh.account_id"
                + where_clause
                + " AND (SELECT COUNT(*) FROM balance_history bh2 "
                "       WHERE bh2.account_id = bh.account_id "
                "         AND bh2.as_of_date >= bh.as_of_date) <= ?"
                " ORDER BY a.name, bh.as_of_date DESC"
            )
            params.append(limit)
        else:
            query = (
                "SELECT a.name AS account, a.account_type, bh.as_of_date, "
                "bh.balance, bh.source, bh.notes "
                "FROM balance_history bh "
                "JOIN accounts a ON a.id = bh.account_id"
                + where_clause
                + " ORDER BY a.name, bh.as_of_date DESC"
            )

        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    snapshots = [dict(r) for r in rows]

    payload = {
        "ok": True,
        "count": len(snapshots),
        "filters": {"account": account, "since": since, "limit": limit},
        "snapshots": snapshots,
    }

    def _render(p: dict) -> None:
        if not p["snapshots"]:
            click.echo("No balance snapshots recorded.")
            return
        current_account = None
        for s in p["snapshots"]:
            if s["account"] != current_account:
                current_account = s["account"]
                click.echo(f"\n{current_account} ({s['account_type']}):")
            line = f"  {s['as_of_date']}  ${s['balance']:>12,.2f}  ({s['source']})"
            if s["notes"]:
                line += f"  — {s['notes']}"
            click.echo(line)
        click.echo(f"\nTotal snapshots: {p['count']}")

    emit(ctx, payload, _render)
