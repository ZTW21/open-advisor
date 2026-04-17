"""`finance cashflow` — summarize inflows and outflows over a window.

Groups transactions by category, account, or merchant and returns totals
plus a breakdown. Transfers are excluded by default so the numbers reflect
actual household spend, not internal shuffling.

Typical usage:

    finance cashflow --last 30d                # last 30 days by category
    finance cashflow --last 7d --by merchant   # last week by merchant
    finance cashflow --month 2026-03           # full March
"""

from __future__ import annotations

from datetime import date, datetime

import click

from finance_advisor.analytics import (
    bucket_to_dict,
    cashflow_by,
    cashflow_totals,
    parse_month,
    parse_window,
)
from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect
from finance_advisor.output import emit, emit_error


@click.command("cashflow")
@click.option("--last", default="30d", show_default=True,
              help="Window: 7d, 30d, 90d, 1y. Ignored if --month is given.")
@click.option("--month", default=None, help="Specific month: YYYY-MM.")
@click.option("--by", default="category", show_default=True,
              type=click.Choice(["category", "account", "merchant"]),
              help="How to group the breakdown.")
@click.option("--include-transfers", is_flag=True, default=False,
              help="Include transfer rows (default: excluded).")
@click.option("--limit", default=15, show_default=True, type=int,
              help="Max breakdown rows to return.")
@click.pass_context
def cashflow(ctx: click.Context, last: str, month: str | None,
             by: str, include_transfers: bool, limit: int) -> None:
    """Summarize inflows and outflows over a window."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    try:
        if month:
            start, end = parse_month(month)
            window_label = month
        else:
            start, end = parse_window(last)
            window_label = last
    except ValueError as e:
        emit_error(ctx, str(e), code="bad_window")
        return

    conn = connect(config.db_path)
    try:
        totals = cashflow_totals(conn, start, end, include_transfers=include_transfers)
        buckets = cashflow_by(conn, start, end, by=by, include_transfers=include_transfers)
    finally:
        conn.close()

    breakdown = [bucket_to_dict(b) for b in buckets[:limit]]
    payload = {
        "ok": True,
        "window": {
            "label": window_label,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": (end - start).days + 1,
        },
        "by": by,
        "include_transfers": include_transfers,
        "totals": totals,
        "breakdown": breakdown,
        "breakdown_truncated_to": limit,
        "breakdown_total_rows": len(buckets),
    }

    def _render(p: dict) -> None:
        w = p["window"]
        t = p["totals"]
        click.echo(
            f"Cashflow {w['start']} → {w['end']} ({w['days']}d):"
        )
        click.echo(f"  Inflow:  ${t['inflow']:>12,.2f}")
        click.echo(f"  Outflow: ${t['outflow']:>12,.2f}")
        click.echo(f"  Net:     ${t['net']:>12,.2f}  ({t['count']} txns)")
        if not p["breakdown"]:
            click.echo(f"\nNo transactions in this window.")
            return
        click.echo(f"\nBy {p['by']}:")
        for b in p["breakdown"]:
            click.echo(
                f"  {b['key'][:28]:<28} "
                f"in ${b['inflow']:>10,.2f}  "
                f"out ${b['outflow']:>10,.2f}  "
                f"({b['count']})"
            )
        if p["breakdown_total_rows"] > len(p["breakdown"]):
            click.echo(
                f"  ... and {p['breakdown_total_rows'] - len(p['breakdown'])} more "
                f"(--limit to see more)"
            )

    emit(ctx, payload, _render)
