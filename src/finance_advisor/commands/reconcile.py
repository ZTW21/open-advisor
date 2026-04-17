"""`finance reconcile` — compare computed balances to user-supplied statement totals.

STUB: wired in Phase 5.

The real implementation will take an account + expected ending balance + as-of
date, sum transactions, and report drift (missing/extra transactions).
"""

from __future__ import annotations

import click

from finance_advisor.output import not_yet_implemented


@click.command("reconcile")
@click.option("--account", required=True, help="Account name to reconcile.")
@click.option("--balance", required=True, type=float, help="Expected statement balance.")
@click.option("--as-of", required=True, help="Statement date: YYYY-MM-DD.")
@click.pass_context
def reconcile(ctx: click.Context, account: str, balance: float, as_of: str) -> None:
    """Reconcile an account against a statement balance."""
    not_yet_implemented(ctx, "reconcile", "Phase 5")
