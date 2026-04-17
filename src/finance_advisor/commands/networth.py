"""`finance net-worth` — compute current net worth from the database.

Net worth = sum of latest balances across active accounts, signed by account type:
  - Assets (checking, savings, brokerage, retirement): + balance
  - Liabilities (credit_card, loan, mortgage): - balance

We report the number, the breakdown by account, and the "as of" date of the
oldest balance we're using — so the user can see how stale the picture is.

Returns zero with no accounts when the database is empty (Phase 1 success
criterion: `finance init && finance net-worth --json` returns a valid result).
"""

from __future__ import annotations

from decimal import Decimal

import click

from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect
from finance_advisor.output import emit


ASSET_TYPES = {"checking", "savings", "brokerage", "retirement", "cash", "other"}
LIABILITY_TYPES = {"credit_card", "loan", "mortgage"}


def _sign_for(account_type: str) -> int:
    if account_type in ASSET_TYPES:
        return 1
    if account_type in LIABILITY_TYPES:
        return -1
    # Unknown types treated as assets for now; surfaced in breakdown.
    return 1


@click.command("net-worth")
@click.option(
    "--as-of",
    default=None,
    help="Use balances as of this date (YYYY-MM-DD). Default: latest.",
)
@click.pass_context
def net_worth(ctx: click.Context, as_of: str | None) -> None:
    """Compute net worth from current account balances."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    conn = connect(config.db_path)
    try:
        # Get all active accounts
        accounts = conn.execute(
            "SELECT id, name, institution, account_type, currency "
            "FROM accounts WHERE active = 1 ORDER BY name"
        ).fetchall()

        breakdown = []
        assets_total = Decimal("0")
        liabilities_total = Decimal("0")
        oldest_as_of: str | None = None

        for a in accounts:
            # Latest balance for this account, optionally bounded by as_of
            if as_of:
                row = conn.execute(
                    "SELECT as_of_date, balance, source FROM balance_history "
                    "WHERE account_id = ? AND as_of_date <= ? "
                    "ORDER BY as_of_date DESC LIMIT 1",
                    (a["id"], as_of),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT as_of_date, balance, source FROM balance_history "
                    "WHERE account_id = ? ORDER BY as_of_date DESC LIMIT 1",
                    (a["id"],),
                ).fetchone()

            if row is None:
                breakdown.append(
                    {
                        "account": a["name"],
                        "account_type": a["account_type"],
                        "balance": None,
                        "as_of_date": None,
                        "source": None,
                        "signed_contribution": 0.0,
                    }
                )
                continue

            balance = Decimal(str(row["balance"]))
            sign = _sign_for(a["account_type"])
            contribution = balance * sign

            if a["account_type"] in LIABILITY_TYPES:
                liabilities_total += balance
            else:
                assets_total += balance

            if oldest_as_of is None or row["as_of_date"] < oldest_as_of:
                oldest_as_of = row["as_of_date"]

            breakdown.append(
                {
                    "account": a["name"],
                    "account_type": a["account_type"],
                    "balance": float(balance),
                    "as_of_date": row["as_of_date"],
                    "source": row["source"],
                    "signed_contribution": float(contribution),
                }
            )
    finally:
        conn.close()

    net = assets_total - liabilities_total

    payload = {
        "ok": True,
        "net_worth": float(net),
        "assets_total": float(assets_total),
        "liabilities_total": float(liabilities_total),
        "currency": "USD",
        "as_of_requested": as_of,
        "oldest_balance_as_of": oldest_as_of,
        "account_count": len(accounts),
        "breakdown": breakdown,
    }

    def _render(p: dict) -> None:
        if p["account_count"] == 0:
            click.echo("No accounts registered yet.")
            click.echo("Use `finance account add` to register one.")
            click.echo("\nNet worth: $0.00")
            return
        click.echo(f"Net worth: ${p['net_worth']:,.2f}")
        click.echo(f"  Assets:      ${p['assets_total']:,.2f}")
        click.echo(f"  Liabilities: ${p['liabilities_total']:,.2f}")
        if p["oldest_balance_as_of"]:
            click.echo(f"  Oldest data point: {p['oldest_balance_as_of']}")
        click.echo("\nBreakdown:")
        for b in p["breakdown"]:
            if b["balance"] is None:
                click.echo(f"  {b['account']:<25} {b['account_type']:<14} (no balance recorded)")
            else:
                click.echo(
                    f"  {b['account']:<25} {b['account_type']:<14} "
                    f"${b['balance']:>12,.2f}  as of {b['as_of_date']}"
                )

    emit(ctx, payload, _render)
