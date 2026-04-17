"""`finance afford <amount>` — can the user afford a purchase?

Produces a payload the advisor uses to answer "can I afford X?" with honest
tradeoffs. The command never says yes/no on its own — it returns the inputs
and a verdict (`green` | `yellow` | `red`). The AI composes the explanation.

Logic (from `routines/afford.md`):
  1. **Cushion check**: would paying `amount` out of liquid cash leave an
     emergency fund of at least `--min-months` of trailing monthly outflow?
  2. **Pace check**: is `amount` less than one month's free cash (income − outflow)?
  3. **Goal impact**: for active goals with a target date, estimate how many
     extra months the reduction would push each out by.

Verdict:
  - green  — cushion above threshold AND ≤ 1× monthly free cash
  - yellow — cushion above threshold but above free cash (dips into savings)
  - red    — would drop cushion below threshold OR no cushion data available
"""

from __future__ import annotations

from datetime import date

import click

from finance_advisor.analytics import (
    goal_pace_impact,
    liquid_cash,
    savings_rate,
    trailing_monthly_outflow,
)
from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect
from finance_advisor.output import emit, emit_error


@click.command("afford")
@click.argument("amount", type=float)
@click.option(
    "--min-months",
    default=3.0,
    show_default=True,
    help="Minimum emergency-fund cushion (months of trailing outflow). "
    "Users with stable incomes often prefer 3; volatile 6+.",
)
@click.option(
    "--as-of",
    default=None,
    help="Evaluate as of this date (YYYY-MM-DD). Default: today.",
)
@click.pass_context
def afford(
    ctx: click.Context,
    amount: float,
    min_months: float,
    as_of: str | None,
) -> None:
    """Assess whether a purchase of `amount` is affordable."""
    if amount <= 0:
        emit_error(ctx, "Amount must be positive.", code="invalid_amount")
        return
    if min_months < 0:
        emit_error(ctx, "--min-months must be non-negative.", code="invalid_min_months")
        return

    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)
    as_of_date = date.fromisoformat(as_of) if as_of else date.today()

    conn = connect(config.db_path)
    try:
        cash = liquid_cash(conn, as_of_date)
        outflow = trailing_monthly_outflow(conn, as_of_date, months=3)
        # Savings rate looks at the last 3 months for the pace check.
        from datetime import timedelta
        sr_end = as_of_date
        sr_start = sr_end - timedelta(days=90)
        sr = savings_rate(conn, sr_start, sr_end)
        goal_impact = goal_pace_impact(conn, as_of_date, reduction=amount)
    finally:
        conn.close()

    monthly_outflow = outflow["monthly_average"]
    cushion_before = cash["total"]
    cushion_after = cushion_before - amount
    months_after = (
        cushion_after / monthly_outflow if monthly_outflow > 0 else None
    )
    months_before = (
        cushion_before / monthly_outflow if monthly_outflow > 0 else None
    )

    # 90-day monthly free cash (a rough "does it fit in one month" number).
    # savings_rate.saved is for the whole 90d window; divide by 3 for monthly.
    monthly_free_cash = (sr["saved"] / 3.0) if sr["saved"] is not None else None
    fits_in_free_cash = (
        monthly_free_cash is not None
        and amount <= monthly_free_cash
    )

    # Verdict logic.
    if monthly_outflow <= 0:
        # Can't assess a cushion without outflow history.
        verdict = "red"
        verdict_reason = "no_outflow_history"
    elif months_after is None or months_after < min_months:
        verdict = "red"
        verdict_reason = "breaches_cushion"
    elif fits_in_free_cash:
        verdict = "green"
        verdict_reason = "fits_in_monthly_free_cash"
    else:
        verdict = "yellow"
        verdict_reason = "dips_into_savings_but_keeps_cushion"

    payload = {
        "ok": True,
        "as_of": as_of_date.isoformat(),
        "amount": amount,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "cushion": {
            "min_months_required": min_months,
            "liquid_cash_before": round(cushion_before, 2),
            "liquid_cash_after": round(cushion_after, 2),
            "monthly_outflow": monthly_outflow,
            "months_of_cushion_before": (
                round(months_before, 1) if months_before is not None else None
            ),
            "months_of_cushion_after": (
                round(months_after, 1) if months_after is not None else None
            ),
            "breakdown": cash["breakdown"],
        },
        "pace": {
            "window_start": sr_start.isoformat(),
            "window_end": sr_end.isoformat(),
            "monthly_free_cash_est": (
                round(monthly_free_cash, 2) if monthly_free_cash is not None else None
            ),
            "fits_in_monthly_free_cash": fits_in_free_cash,
            "savings_rate": (
                round(sr["rate"], 4) if sr["rate"] is not None else None
            ),
        },
        "goal_impact": goal_impact,
    }

    def _render(p: dict) -> None:
        c = p["cushion"]
        click.echo(f"Affordability check: ${p['amount']:,.2f}")
        click.echo(f"  Verdict: {p['verdict'].upper()}  ({p['verdict_reason']})")
        click.echo("")
        click.echo("  Cushion:")
        click.echo(f"    Liquid cash before: ${c['liquid_cash_before']:,.2f}")
        click.echo(f"    Liquid cash after:  ${c['liquid_cash_after']:,.2f}")
        if c["monthly_outflow"]:
            click.echo(
                f"    Monthly outflow:    ${c['monthly_outflow']:,.2f} "
                f"({c['months_of_cushion_before']}mo → {c['months_of_cushion_after']}mo)"
            )
            click.echo(
                f"    Minimum required:   {c['min_months_required']}mo"
            )
        else:
            click.echo("    Monthly outflow:    (no history)")
        pace = p["pace"]
        click.echo("")
        click.echo("  Pace:")
        if pace["monthly_free_cash_est"] is not None:
            click.echo(
                f"    Monthly free cash est: ${pace['monthly_free_cash_est']:,.2f} "
                f"({pace['window_start']} → {pace['window_end']})"
            )
            fits = "yes" if pace["fits_in_monthly_free_cash"] else "no"
            click.echo(f"    Fits in one month:    {fits}")
        else:
            click.echo("    (no income/outflow data for the trailing 90 days)")
        if p["goal_impact"]:
            click.echo("")
            click.echo("  Goal impact (if pulled from future savings):")
            for g in p["goal_impact"]:
                extra = (
                    f"+{g['extra_months_to_target']}mo"
                    if g["extra_months_to_target"] is not None
                    else "—"
                )
                click.echo(
                    f"    {g['goal']:<25} share ${g['share_of_reduction']:,.2f}  "
                    f"slip: {extra}"
                )

    emit(ctx, payload, _render)
