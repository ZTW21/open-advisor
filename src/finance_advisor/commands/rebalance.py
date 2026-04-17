"""`finance rebalance` — compare current allocation to target, flag drift.

Phase 9: compares balance-level asset-class allocation (sourced from
`accounts.asset_class`, falling back to `analytics.DEFAULT_ASSET_CLASS_BY_TYPE`)
against the user's `allocation_targets` table.

Gives advice at the **asset-class level only** — per CLAUDE.md §2, we don't
name specific tickers. The advisor reads this payload and suggests, e.g.,
"shift 4% from bonds to international stocks" — never "sell 12 shares of BND."

When targets haven't been set, the command emits the current allocation with
`targets_set: false` so the advisor can walk the user through setting them.
"""

from __future__ import annotations

from datetime import date

import click

from finance_advisor.analytics import (
    allocation_targets,
    current_allocation,
)
from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect
from finance_advisor.output import emit, emit_error


def _classify_drift(drift_pct: float, tolerance: float) -> str:
    """Categorize drift magnitude vs. the user's tolerance."""
    magnitude = abs(drift_pct)
    if magnitude <= tolerance:
        return "on_target"
    if magnitude <= 2 * tolerance:
        return "warn"
    return "breach"


@click.command("rebalance")
@click.option(
    "--tolerance",
    default=5.0,
    show_default=True,
    help="Drift tolerance in percentage points. Classes within ±tolerance are "
    "'on_target'; up to 2× are 'warn'; beyond are 'breach'.",
)
@click.option(
    "--as-of",
    default=None,
    help="Use allocations as of this date (YYYY-MM-DD). Default: today.",
)
@click.pass_context
def rebalance(ctx: click.Context, tolerance: float, as_of: str | None) -> None:
    """Compare current allocation to target and flag drift."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    as_of_date = date.fromisoformat(as_of) if as_of else date.today()

    if tolerance < 0:
        emit_error(ctx, "--tolerance must be non-negative.", code="invalid_tolerance")
        return

    conn = connect(config.db_path)
    try:
        current = current_allocation(conn, as_of_date)
        targets_obj = allocation_targets(conn, as_of_date)
    finally:
        conn.close()

    current_map = {c["asset_class"]: c for c in current["by_class"]}
    targets = targets_obj["targets"]

    # Build the union of asset classes present on either side so under-weights
    # (classes with 0% current but a target) get flagged.
    all_classes = sorted(set(current_map.keys()) | set(targets.keys()))

    drift_rows = []
    for ac in all_classes:
        cur_pct = current_map[ac]["pct"] if ac in current_map else 0.0
        cur_bal = current_map[ac]["balance"] if ac in current_map else 0.0
        tgt_pct = targets.get(ac)  # None if no target for this class
        if tgt_pct is None:
            drift_rows.append({
                "asset_class": ac,
                "current_pct": cur_pct,
                "current_balance": cur_bal,
                "target_pct": None,
                "drift_pp": None,
                "drift_dollars": None,
                "status": "untargeted",
            })
            continue
        drift_pp = round(cur_pct - tgt_pct, 2)
        drift_dollars = round(
            current["assets_total"] * drift_pp / 100.0, 2
        ) if current["assets_total"] else 0.0
        drift_rows.append({
            "asset_class": ac,
            "current_pct": cur_pct,
            "current_balance": cur_bal,
            "target_pct": tgt_pct,
            "drift_pp": drift_pp,
            "drift_dollars": drift_dollars,
            "status": _classify_drift(drift_pp, tolerance),
        })

    # Suggestions: only for classes with explicit targets outside tolerance.
    suggestions = []
    for row in drift_rows:
        if row["status"] in ("on_target", "untargeted"):
            continue
        if row["drift_pp"] is None:
            continue
        direction = "reduce" if row["drift_pp"] > 0 else "add to"
        suggestions.append({
            "asset_class": row["asset_class"],
            "direction": direction,
            "drift_pp": row["drift_pp"],
            "drift_dollars": row["drift_dollars"],
            "status": row["status"],
            "note": (
                f"{direction.title()} {row['asset_class']} by "
                f"{abs(row['drift_pp']):.1f}pp "
                f"(≈ ${abs(row['drift_dollars']):,.0f})."
            ),
        })
    # Worst drift first.
    suggestions.sort(key=lambda s: -abs(s["drift_pp"]))

    targets_total = targets_obj["total_pct"]
    targets_warnings = []
    if targets and abs(targets_total - 100.0) > 0.5:
        targets_warnings.append(
            f"Targets sum to {targets_total:.1f}%, not 100%. "
            "Review the allocation_targets table."
        )

    payload = {
        "ok": True,
        "as_of": as_of_date.isoformat(),
        "tolerance_pp": tolerance,
        "targets_set": bool(targets),
        "assets_total": current["assets_total"],
        "current_allocation": current["by_class"],
        "targets": targets,
        "drift": drift_rows,
        "suggestions": suggestions,
        "missing_balance_accounts": current["missing_balance"],
        "warnings": targets_warnings,
    }

    def _render(p: dict) -> None:
        click.echo(f"Rebalance check (as of {p['as_of']})")
        if not p["targets_set"]:
            click.echo("  No allocation targets set.")
            click.echo("  Current allocation:")
            for c in p["current_allocation"]:
                click.echo(
                    f"    {c['asset_class']:<13} ${c['balance']:>12,.2f}  "
                    f"({c['pct']:>5.1f}%)"
                )
            click.echo(
                "\n  Set targets by inserting rows into `allocation_targets`."
            )
            return
        click.echo(
            f"  Assets total: ${p['assets_total']:,.2f}  "
            f"(tolerance ±{p['tolerance_pp']:.1f}pp)"
        )
        click.echo("")
        click.echo(f"  {'Class':<13} {'Current':>9}  {'Target':>8}  {'Drift':>8}  Status")
        for row in p["drift"]:
            tgt = f"{row['target_pct']:.1f}%" if row["target_pct"] is not None else "—"
            drift = f"{row['drift_pp']:+.1f}pp" if row["drift_pp"] is not None else "—"
            click.echo(
                f"  {row['asset_class']:<13} {row['current_pct']:>8.1f}%  "
                f"{tgt:>8}  {drift:>8}  {row['status']}"
            )
        if p["suggestions"]:
            click.echo("\n  Suggestions:")
            for s in p["suggestions"]:
                click.echo(f"    - {s['note']}")
        if p["missing_balance_accounts"]:
            click.echo(
                "\n  Accounts with no recorded balance (excluded): "
                + ", ".join(p["missing_balance_accounts"])
            )
        for w in p["warnings"]:
            click.echo(f"\n  ⚠ {w}")

    emit(ctx, payload, _render)
