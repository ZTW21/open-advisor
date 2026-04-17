"""`finance fees` — audit recorded account fees.

Quarterly fee audit helper. Reads user-recorded fees on accounts
(`expense_ratio_pct`, `annual_fee`) and reports:

  - total annual cost across all fee-bearing accounts
  - accounts flagged as expensive (expense ratio above `--threshold`)
  - accounts of brokerage/retirement type with no fee info on file
    (suggests the user hasn't yet populated them)

This never touches market-data APIs or fund-level holdings — the CLI
is only as good as the numbers the user enters on each account.

The Boglehead rule of thumb is 0.10–0.25% total cost of ownership.
Default threshold is 0.25%: anything above gets flagged.
"""

from __future__ import annotations

from datetime import date

import click

from finance_advisor.analytics import fee_audit
from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect
from finance_advisor.output import emit, emit_error


@click.command("fees")
@click.option(
    "--threshold",
    default=0.25,
    show_default=True,
    type=float,
    help="Expense-ratio threshold (percent). Accounts above are flagged.",
)
@click.option(
    "--as-of",
    default=None,
    help="Compute balance-weighted costs as of this date (YYYY-MM-DD). "
    "Default: today.",
)
@click.pass_context
def fees(ctx: click.Context, threshold: float, as_of: str | None) -> None:
    """Audit recorded account fees (expense ratios and annual fees)."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    try:
        as_of_date = date.fromisoformat(as_of) if as_of else date.today()
    except ValueError:
        emit_error(ctx, f"Invalid --as-of: {as_of!r}", code="bad_date")
        return

    if threshold < 0:
        emit_error(ctx, "--threshold must be non-negative.", code="invalid_threshold")
        return

    conn = connect(config.db_path)
    try:
        result = fee_audit(conn, as_of_date, threshold_pct=threshold)
    finally:
        conn.close()

    payload = {"ok": True, **result}

    def _render(p: dict) -> None:
        click.echo(f"Fee audit (as of {p['as_of']}, threshold {p['threshold_pct']:.2f}%)")
        if not p["accounts"]:
            click.echo("  No accounts have recorded fees.")
            if p["missing_fee_info"]:
                click.echo(
                    "\n  Brokerage/retirement accounts missing fee info: "
                    + ", ".join(p["missing_fee_info"])
                )
            return

        click.echo(
            f"  Estimated total annual cost: ${p['total_annual_cost']:,.2f}\n"
        )
        click.echo(
            f"  {'Account':<22} {'Balance':>12}  {'ER %':>6}  "
            f"{'Fee $':>8}  {'Annual':>10}"
        )
        for row in p["accounts"]:
            bal = f"${row['balance']:,.0f}" if row["balance"] is not None else "—"
            er = (
                f"{row['expense_ratio_pct']:.3f}"
                if row["expense_ratio_pct"] is not None
                else "—"
            )
            fee = (
                f"${row['annual_fee']:,.0f}"
                if row["annual_fee"] is not None
                else "—"
            )
            click.echo(
                f"  {row['account'][:22]:<22} {bal:>12}  {er:>6}  "
                f"{fee:>8}  ${row['total_annual_cost']:>9,.2f}"
            )

        if p["flagged"]:
            click.echo("\n  Flagged (above threshold):")
            for row in p["flagged"]:
                click.echo(
                    f"    - {row['account']}: {row['expense_ratio_pct']:.3f}% "
                    f"→ ~${row['expense_cost']:,.2f}/yr on "
                    f"${(row['balance'] or 0):,.0f}"
                )

        if p["missing_fee_info"]:
            click.echo(
                "\n  Missing fee info (brokerage/retirement): "
                + ", ".join(p["missing_fee_info"])
            )

    emit(ctx, payload, _render)
