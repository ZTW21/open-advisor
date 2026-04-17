"""`finance payoff` — simulate debt-payoff strategies.

Pulls the debt roster from the database (active liability accounts with a
recorded balance), then runs a month-by-month simulation for the chosen
strategy, optionally comparing alternatives.

Strategies:
  - avalanche  — highest APR first (default; minimizes total interest)
  - snowball   — smallest balance first (maximizes psychological wins)
  - custom     — user-specified order via --order 'name1,name2,...'

Extra monthly principal goes to the top-priority debt until it clears, then
rolls down the line (freed-up minimums also cascade — standard "debt
snowball/avalanche" mechanic).

**This command does not move money.** It advises. The user executes the plan
through their bank.
"""

from __future__ import annotations

from datetime import date

import click

from finance_advisor.analytics import debt_roster, simulate_payoff
from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect
from finance_advisor.output import emit, emit_error


@click.command("payoff")
@click.option(
    "--strategy",
    type=click.Choice(["avalanche", "snowball", "custom"]),
    default="avalanche",
    show_default=True,
    help="Ordering rule for extra principal.",
)
@click.option(
    "--extra",
    default=0.0,
    show_default=True,
    type=float,
    help="Extra dollars per month to apply toward principal (on top of minimums).",
)
@click.option(
    "--order",
    "custom_order",
    default=None,
    help="For --strategy=custom: comma-separated account names in priority order.",
)
@click.option(
    "--compare",
    is_flag=True,
    default=False,
    help="Also run the alternative strategy (avalanche vs. snowball) for comparison.",
)
@click.option(
    "--as-of",
    default=None,
    help="Use balances as of this date (YYYY-MM-DD). Default: today.",
)
@click.pass_context
def payoff(
    ctx: click.Context,
    strategy: str,
    extra: float,
    custom_order: str | None,
    compare: bool,
    as_of: str | None,
) -> None:
    """Simulate debt payoff and surface the months-to-freedom number."""
    if extra < 0:
        emit_error(ctx, "--extra must be non-negative.", code="invalid_extra")
        return

    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)
    as_of_date = date.fromisoformat(as_of) if as_of else date.today()

    conn = connect(config.db_path)
    try:
        debts = debt_roster(conn, as_of_date)
    finally:
        conn.close()

    if not debts:
        emit(
            ctx,
            {
                "ok": True,
                "as_of": as_of_date.isoformat(),
                "no_debts": True,
                "message": (
                    "No active debt accounts with a recorded balance. "
                    "Add one with `finance account add --type credit_card ...` "
                    "and post a balance."
                ),
            },
            lambda p: click.echo(p["message"]),
        )
        return

    parsed_order: list[str] | None = None
    if strategy == "custom":
        if not custom_order:
            emit_error(
                ctx,
                "--strategy=custom requires --order 'name1,name2,...'.",
                code="missing_order",
            )
            return
        parsed_order = [s.strip() for s in custom_order.split(",") if s.strip()]
        known = {d.name for d in debts}
        unknown = [n for n in parsed_order if n not in known]
        if unknown:
            emit_error(
                ctx,
                f"Unknown account names in --order: {unknown}. Known: {sorted(known)}.",
                code="unknown_accounts",
                details={"unknown": unknown, "known": sorted(known)},
            )
            return

    primary = simulate_payoff(
        debts,
        strategy=strategy,
        extra_monthly=extra,
        custom_order=parsed_order,
    )

    comparison = None
    if compare and strategy in ("avalanche", "snowball"):
        alt = "snowball" if strategy == "avalanche" else "avalanche"
        comparison = simulate_payoff(debts, strategy=alt, extra_monthly=extra)

    roster = [
        {
            "name": d.name,
            "account_type": d.account_type,
            "balance": round(d.balance, 2),
            "apr": d.apr,
            "min_payment": d.min_payment,
            "as_of_date": d.as_of_date,
        }
        for d in debts
    ]
    total_balance = round(sum(d.balance for d in debts), 2)
    total_min_payment = round(
        sum(d.min_payment for d in debts if d.min_payment is not None), 2
    )

    payload = {
        "ok": True,
        "as_of": as_of_date.isoformat(),
        "strategy": strategy,
        "extra_monthly": extra,
        "debt_roster": roster,
        "total_balance": total_balance,
        "total_min_payment": total_min_payment,
        "result": primary,
        "comparison": comparison,
    }

    def _render(p: dict) -> None:
        click.echo(
            f"Debt payoff  (as of {p['as_of']}, strategy={p['strategy']}, "
            f"extra ${p['extra_monthly']:,.2f}/mo)"
        )
        click.echo("")
        click.echo("  Current debts:")
        for r in p["debt_roster"]:
            apr = f"{r['apr']:.2f}%" if r["apr"] is not None else "—"
            minp = f"${r['min_payment']:,.2f}" if r["min_payment"] is not None else "—"
            click.echo(
                f"    {r['name']:<20} ${r['balance']:>10,.2f}  APR {apr:>7}  min {minp:>10}"
            )
        click.echo(
            f"    {'TOTAL':<20} ${p['total_balance']:>10,.2f}  "
            f"min ${p['total_min_payment']:,.2f}/mo"
        )
        click.echo("")
        res = p["result"]
        if not res["converged"]:
            click.echo("  ⚠ Simulation did not converge — extra too small to cover interest.")
        else:
            months = res["months"]
            years = months / 12.0
            click.echo(
                f"  Months to debt-free: {months}  ({years:.1f}yr)  "
                f"Total interest: ${res['total_interest']:,.2f}"
            )
            click.echo("  Per-debt timing:")
            for d in res["by_debt"]:
                m = d["months_to_zero"]
                label = f"{m}mo" if m is not None else "—"
                click.echo(
                    f"    {d['name']:<20} cleared in {label:<8}  "
                    f"interest ${d['interest_paid']:,.2f}"
                )
        for w in res.get("warnings", []):
            click.echo(f"  ⚠ {w}")
        if p["comparison"]:
            c = p["comparison"]
            click.echo("")
            click.echo(
                f"  Alternative ({c['strategy']}): {c['months']}mo, "
                f"interest ${c['total_interest']:,.2f}"
            )
            diff = res["total_interest"] - c["total_interest"]
            if diff < 0:
                click.echo(
                    f"    → {p['strategy']} saves ${-diff:,.2f} vs. {c['strategy']}."
                )
            elif diff > 0:
                click.echo(
                    f"    → {c['strategy']} saves ${diff:,.2f} vs. {p['strategy']}."
                )
            else:
                click.echo("    → same total interest either way.")

    emit(ctx, payload, _render)
