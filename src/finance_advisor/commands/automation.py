"""`finance automation` — surface recurring outflows for the automation audit.

The semiannual automation audit (see `routines/automation-audit.md`) reviews
every recurring debit hitting the user's accounts: subscriptions, auto-pays,
streaming services, app store charges, gym memberships, etc.

This command returns the raw list. The advisor groups it, prices the annual
cost, and walks the user through keep/kill decisions.
"""

from __future__ import annotations

from datetime import date

import click

from finance_advisor.analytics import detect_recurring
from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect
from finance_advisor.output import emit, emit_error


@click.command("automation")
@click.option(
    "--lookback-months",
    default=6,
    show_default=True,
    type=int,
    help="How many trailing full months to scan.",
)
@click.option(
    "--min-hits",
    default=3,
    show_default=True,
    type=int,
    help="Minimum number of distinct months a merchant must appear in.",
)
@click.option(
    "--tolerance",
    default=0.15,
    show_default=True,
    type=float,
    help="Amount stability: charges must be within this fraction of "
    "the median (0.15 = ±15%).",
)
@click.option(
    "--as-of",
    default=None,
    help="Audit as of this date (YYYY-MM-DD). Default: today.",
)
@click.pass_context
def automation(
    ctx: click.Context,
    lookback_months: int,
    min_hits: int,
    tolerance: float,
    as_of: str | None,
) -> None:
    """List recurring outflows detected over the lookback window."""
    if lookback_months <= 0:
        emit_error(ctx, "--lookback-months must be positive.", code="bad_lookback")
        return
    if min_hits <= 0:
        emit_error(ctx, "--min-hits must be positive.", code="bad_min_hits")
        return
    if tolerance < 0:
        emit_error(ctx, "--tolerance must be non-negative.", code="bad_tolerance")
        return

    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    try:
        as_of_date = date.fromisoformat(as_of) if as_of else date.today()
    except ValueError:
        emit_error(ctx, f"Invalid --as-of: {as_of!r}", code="bad_date")
        return

    conn = connect(config.db_path)
    try:
        recurring = detect_recurring(
            conn,
            as_of_date,
            lookback_months=lookback_months,
            min_hits=min_hits,
            amount_tolerance=tolerance,
        )
    finally:
        conn.close()

    total_annual = round(sum(r["estimated_annual"] for r in recurring), 2)
    payload = {
        "ok": True,
        "as_of": as_of_date.isoformat(),
        "lookback_months": lookback_months,
        "min_hits": min_hits,
        "tolerance": tolerance,
        "recurring": recurring,
        "total_estimated_annual": total_annual,
    }

    def _render(p: dict) -> None:
        click.echo(
            f"Automation audit (as of {p['as_of']}, "
            f"{p['lookback_months']}mo lookback)"
        )
        if not p["recurring"]:
            click.echo("  No recurring outflows detected.")
            return
        click.echo(
            f"  Estimated total annual cost: ${p['total_estimated_annual']:,.2f}"
        )
        click.echo("")
        click.echo(
            f"  {'Merchant':<28} {'Category':<18} {'Monthly':>10}  "
            f"{'Annual':>10}  {'Hits':>5}"
        )
        for r in p["recurring"]:
            click.echo(
                f"  {r['merchant'][:28]:<28} {r['category'][:18]:<18} "
                f"${r['estimated_monthly']:>9,.2f}  "
                f"${r['estimated_annual']:>9,.2f}  "
                f"{r['hits']:>5}"
            )

    emit(ctx, payload, _render)
