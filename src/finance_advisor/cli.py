"""Root CLI entry point for the `finance` command."""

from __future__ import annotations

import click

from finance_advisor import __version__
from finance_advisor.commands import (
    account,
    afford,
    anomalies,
    automation,
    backup,
    balance,
    cashflow,
    categorize,
    export,
    fees,
    import_,
    init,
    mode,
    networth,
    payoff,
    rebalance,
    reconcile,
    report,
    sync,
    taxpack,
)


@click.group()
@click.version_option(version=__version__, prog_name="finance")
@click.option(
    "--db",
    "db_override",
    envvar="FINANCE_DB",
    default=None,
    type=click.Path(),
    help="Path to the SQLite database (overrides auto-discovery).",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    default=False,
    help="Output machine-readable JSON instead of human text.",
)
@click.pass_context
def cli(ctx: click.Context, db_override: str | None, json_output: bool) -> None:
    """Finance advisor CLI — the deterministic layer beneath the AI advisor.

    The AI calls these commands with --json and reads the output.
    You can also run them directly.
    """
    ctx.ensure_object(dict)
    ctx.obj["db_override"] = db_override
    ctx.obj["json_output"] = json_output


# Register subcommands
cli.add_command(init.init)
cli.add_command(account.account)
cli.add_command(balance.balance)
cli.add_command(networth.net_worth)
cli.add_command(cashflow.cashflow)
cli.add_command(anomalies.anomalies)
cli.add_command(report.report)
cli.add_command(import_.import_cmd)
cli.add_command(categorize.categorize)
cli.add_command(reconcile.reconcile)
cli.add_command(rebalance.rebalance)
cli.add_command(afford.afford)
cli.add_command(payoff.payoff)
cli.add_command(export.export)
cli.add_command(backup.backup_cmd)
cli.add_command(fees.fees)
cli.add_command(taxpack.taxpack)
cli.add_command(mode.mode)
cli.add_command(automation.automation)
cli.add_command(sync.sync)


if __name__ == "__main__":
    cli()
