"""`finance anomalies` — surface unusual activity in a window.

Composes the detectors in `finance_advisor.analytics`:
  - large_txn         — a charge that's >= 2x the median for that merchant,
                        or first time over the dollar threshold.
  - new_merchant      — a merchant never seen in the lookback period.
  - category_over_pace — a category running materially above its trailing average.

Everything returned is advisory — nothing is mutated.

Typical usage:

    finance anomalies --since yesterday
    finance anomalies --last 7d --json
    finance anomalies --last 30d --kind new_merchant
"""

from __future__ import annotations

from datetime import date, timedelta

import click

from finance_advisor.analytics import (
    all_anomalies,
    anomaly_to_dict,
    detect_category_over_pace,
    detect_large_transactions,
    detect_new_merchants,
    parse_window,
)
from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect
from finance_advisor.output import emit, emit_error


_KIND_DISPATCH = {
    "large_txn": detect_large_transactions,
    "new_merchant": detect_new_merchants,
    "category_over_pace": detect_category_over_pace,
}


def _parse_since(spec: str, *, today: date | None = None) -> date:
    """Accept 'yesterday', 'today', 'YYYY-MM-DD', or a window like '7d'."""
    today = today or date.today()
    spec = spec.strip().lower()
    if spec == "today":
        return today
    if spec == "yesterday":
        return today - timedelta(days=1)
    # Try raw ISO date
    try:
        from finance_advisor.normalize import parse_date
        return date.fromisoformat(parse_date(spec))
    except (ValueError, ImportError):
        pass
    # Fall back to window
    start, _ = parse_window(spec, today=today)
    return start


@click.command("anomalies")
@click.option("--last", default=None,
              help="Window like '7d', '30d'. Ignored if --since is given.")
@click.option("--since", default=None,
              help="Start date — YYYY-MM-DD, 'yesterday', 'today', or '7d'.")
@click.option("--kind", default="all", show_default=True,
              type=click.Choice(["all", "large_txn", "new_merchant", "category_over_pace"]),
              help="Restrict to a single detector.")
@click.pass_context
def anomalies(ctx: click.Context, last: str | None, since: str | None, kind: str) -> None:
    """Surface unusual activity (large txns, new merchants, category over pace)."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    today = date.today()
    try:
        if since:
            start = _parse_since(since, today=today)
            end = today
        elif last:
            start, end = parse_window(last, today=today)
        else:
            start, end = parse_window("7d", today=today)
    except ValueError as e:
        emit_error(ctx, str(e), code="bad_window")
        return

    conn = connect(config.db_path)
    try:
        if kind == "all":
            found = all_anomalies(conn, start, end)
        else:
            found = _KIND_DISPATCH[kind](conn, start, end)
    finally:
        conn.close()

    payload = {
        "ok": True,
        "window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": (end - start).days + 1,
        },
        "kind_filter": kind,
        "count": len(found),
        "anomalies": [anomaly_to_dict(a) for a in found],
    }

    def _render(p: dict) -> None:
        w = p["window"]
        click.echo(f"Anomalies {w['start']} → {w['end']} ({p['count']} found):")
        if p["count"] == 0:
            click.echo("  Nothing unusual.")
            return
        for a in p["anomalies"]:
            marker = {"alert": "!!", "warn": "! ", "info": "· "}.get(a["severity"], "  ")
            click.echo(f"  {marker} [{a['kind']}] {a['detail']}")

    emit(ctx, payload, _render)
