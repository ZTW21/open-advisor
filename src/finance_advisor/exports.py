"""JSON export helpers.

The .sqlite file is git-ignored. After every committed write, we regenerate
canonical JSON snapshots in data/exports/ so git history stays readable.

Exports are deterministic: same DB state = same JSON output (stable sort,
ISO dates, two-decimal rounding on amounts).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


def export_accounts(conn: sqlite3.Connection, out_dir: Path) -> Path:
    rows = conn.execute(
        "SELECT id, name, institution, account_type, currency, "
        "active, opened_on, closed_on, notes, created_at, updated_at "
        "FROM accounts ORDER BY id"
    ).fetchall()
    out = out_dir / "accounts.json"
    out.write_text(json.dumps(_rows_to_dicts(rows), indent=2, sort_keys=True))
    return out


def export_transactions(conn: sqlite3.Connection, out_dir: Path) -> list[Path]:
    """Export transactions grouped by year-month, one file each."""
    rows = conn.execute(
        "SELECT strftime('%Y-%m', date) AS ym, "
        "id, account_id, date, amount, merchant_normalized, "
        "description_raw, category_id, notes, pending, "
        "transfer_group_id, import_batch_id, dedup_key, created_at "
        "FROM transactions ORDER BY date, id"
    ).fetchall()

    by_month: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        d = dict(r)
        ym = d.pop("ym")
        by_month.setdefault(ym, []).append(d)

    written: list[Path] = []
    for ym, items in sorted(by_month.items()):
        out = out_dir / f"transactions-{ym}.json"
        out.write_text(json.dumps(items, indent=2, sort_keys=True))
        written.append(out)
    return written


def export_holdings(conn: sqlite3.Connection, out_dir: Path) -> Path:
    rows = conn.execute(
        "SELECT id, account_id, ticker, shares, cost_basis, as_of_date, created_at "
        "FROM holdings ORDER BY as_of_date, account_id, ticker"
    ).fetchall()
    out = out_dir / "holdings.json"
    out.write_text(json.dumps(_rows_to_dicts(rows), indent=2, sort_keys=True))
    return out


def export_net_worth_history(conn: sqlite3.Connection, out_dir: Path) -> Path:
    rows = conn.execute(
        "SELECT account_id, as_of_date, balance, source, notes "
        "FROM balance_history ORDER BY as_of_date, account_id"
    ).fetchall()
    out = out_dir / "net-worth-history.json"
    out.write_text(json.dumps(_rows_to_dicts(rows), indent=2, sort_keys=True))
    return out


def export_all(conn: sqlite3.Connection, out_dir: Path) -> dict[str, Any]:
    """Regenerate all standard JSON exports. Return a summary."""
    out_dir.mkdir(parents=True, exist_ok=True)
    accounts_path = export_accounts(conn, out_dir)
    holdings_path = export_holdings(conn, out_dir)
    nwh_path = export_net_worth_history(conn, out_dir)
    tx_paths = export_transactions(conn, out_dir)
    return {
        "accounts": str(accounts_path.relative_to(out_dir.parent.parent)),
        "holdings": str(holdings_path.relative_to(out_dir.parent.parent)),
        "net_worth_history": str(nwh_path.relative_to(out_dir.parent.parent)),
        "transactions": [str(p.relative_to(out_dir.parent.parent)) for p in tx_paths],
    }
