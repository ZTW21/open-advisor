"""`finance tax-pack` — year-end data pack for tax filing handoff.

Aggregates a calendar year's income, spending by category, and net
worth anchors. The output is a structured bundle the advisor turns
into a hand-off document for the user's CPA or filing software.

This is not a tax return. No liability computed, no withholding
adequacy check, no contribution-limit evaluation. Categorical tagging
lives in `transactions/categories.md` — the command trusts what it
finds.

    finance tax-pack --year 2026 --json
"""

from __future__ import annotations

from datetime import date

import click

from finance_advisor.analytics import tax_pack
from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect
from finance_advisor.output import emit, emit_error


@click.command("tax-pack")
@click.option(
    "--year",
    default=None,
    type=int,
    help="Tax year (YYYY). Default: last complete calendar year.",
)
@click.pass_context
def taxpack(ctx: click.Context, year: int | None) -> None:
    """Produce a tax-handoff payload for a given year."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    if year is None:
        year = date.today().year - 1

    if year < 1900 or year > 2999:
        emit_error(ctx, f"Year out of range: {year}", code="bad_year")
        return

    conn = connect(config.db_path)
    try:
        try:
            result = tax_pack(conn, int(year))
        except ValueError as e:
            emit_error(ctx, str(e), code="bad_year")
            return
    finally:
        conn.close()

    payload = {"ok": True, **result}

    def _render(p: dict) -> None:
        click.echo(f"Tax pack — {p['year']}  ({p['start']} → {p['end']})")
        inc = p["income"]
        click.echo(f"\n  Income: ${inc['total']:,.2f}")
        if inc["by_source"]:
            for row in inc["by_source"]:
                click.echo(
                    f"    {row['category'][:28]:<28}  ${row['total']:>12,.2f}  "
                    f"({row['count']} txns)"
                )

        nw = p["net_worth"]
        sign = "+" if nw["delta"] >= 0 else ""
        click.echo(
            f"\n  Net worth: ${nw['beginning']:,.2f} → ${nw['ending']:,.2f}  "
            f"({sign}${nw['delta']:,.2f})"
        )

        if p["spend_by_category"]:
            click.echo("\n  Top spending categories:")
            for row in p["spend_by_category"][:10]:
                click.echo(
                    f"    {row['category'][:28]:<28}  ${row['total']:>12,.2f}  "
                    f"({row['count']} txns)"
                )

        if p["notable"]:
            click.echo("\n  Potentially tax-relevant category matches:")
            for label, rows in p["notable"].items():
                total = sum(r["total"] for r in rows)
                click.echo(f"    {label}: ${total:,.2f} across {len(rows)} cat(s)")

        click.echo(f"\n  {p['disclaimer']}")

    emit(ctx, payload, _render)
