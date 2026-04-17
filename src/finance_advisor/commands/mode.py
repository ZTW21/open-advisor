"""`finance mode` — classify the user into a behavioral mode.

The advisor loads this at the top of a turn to shift tone and prioritization:

  - 'debt'     → high-APR debt present; push extra dollars toward payoff
  - 'invest'   → no problem debt + adequate emergency fund + targets set;
                  focus on contributions, rebalance discipline, compounding
  - 'balanced' → most users, most of the time; balance all three streams

The classification is deterministic: it reads the DB, never estimates, and
exposes its inputs so the advisor can cite which fact drove the decision.
"""

from __future__ import annotations

from datetime import date

import click

from finance_advisor.analytics import mode_detect
from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect
from finance_advisor.output import emit, emit_error


@click.command("mode")
@click.option(
    "--as-of",
    default=None,
    help="Classify as of this date (YYYY-MM-DD). Default: today.",
)
@click.pass_context
def mode(ctx: click.Context, as_of: str | None) -> None:
    """Detect the user's current behavioral mode: debt / invest / balanced."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    try:
        as_of_date = date.fromisoformat(as_of) if as_of else date.today()
    except ValueError:
        emit_error(ctx, f"Invalid --as-of: {as_of!r}", code="bad_date")
        return

    conn = connect(config.db_path)
    try:
        result = mode_detect(conn, as_of_date)
    finally:
        conn.close()

    payload = {"ok": True, **result}

    def _render(p: dict) -> None:
        click.echo(f"Mode: {p['mode']}  (as of {p['as_of']})")
        for r in p["reasons"]:
            click.echo(f"  - {r}")
        inp = p["inputs"]
        click.echo("")
        click.echo("  Inputs:")
        click.echo(
            f"    high-APR debt total: ${inp['high_apr_debt_total']:,.2f} "
            f"(threshold {inp['high_apr_threshold_pct']:.1f}% APR, "
            f"mortgages excluded)"
        )
        if inp["high_apr_accounts"]:
            for a in inp["high_apr_accounts"]:
                click.echo(
                    f"      - {a['name']}: ${a['balance']:,.2f} @ {a['apr']}%"
                )
        click.echo(f"    liquid cash: ${inp['liquid_cash']:,.2f}")
        click.echo(f"    monthly outflow (avg): ${inp['monthly_outflow_avg']:,.2f}")
        ef = inp["emergency_fund_months"]
        if ef is None:
            click.echo("    emergency fund: (unknown — no recent outflow)")
        else:
            click.echo(
                f"    emergency fund: {ef:.1f} months "
                f"(target: {inp['emergency_fund_target_months']:.0f})"
            )
        click.echo(
            f"    allocation targets set: {inp['allocation_targets_set']}"
        )

    emit(ctx, payload, _render)
