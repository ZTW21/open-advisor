"""Account endpoints."""

from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("")
def list_accounts(
    active_only: bool = Query(True),
    conn: sqlite3.Connection = Depends(get_db),
):
    where = "WHERE active = 1" if active_only else ""
    accounts = conn.execute(
        f"SELECT id, name, account_type, active, asset_class, apr, "
        f"min_payment, expense_ratio_pct, annual_fee "
        f"FROM accounts {where} ORDER BY name"
    ).fetchall()

    result = []
    for a in accounts:
        bal_row = conn.execute(
            "SELECT as_of_date, balance FROM balance_history "
            "WHERE account_id = ? ORDER BY as_of_date DESC LIMIT 1",
            (a["id"],),
        ).fetchone()
        result.append({
            "id": a["id"],
            "name": a["name"],
            "account_type": a["account_type"],
            "active": bool(a["active"]),
            "asset_class": a["asset_class"],
            "balance": float(bal_row["balance"]) if bal_row else None,
            "balance_as_of": bal_row["as_of_date"] if bal_row else None,
        })
    return {"ok": True, "accounts": result, "count": len(result)}


@router.get("/{name}")
def get_account(
    name: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    row = conn.execute(
        "SELECT id, name, account_type, active, asset_class, apr, "
        "min_payment, expense_ratio_pct, annual_fee "
        "FROM accounts WHERE name = ?",
        (name,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Account '{name}' not found")

    bal_row = conn.execute(
        "SELECT as_of_date, balance FROM balance_history "
        "WHERE account_id = ? ORDER BY as_of_date DESC LIMIT 1",
        (row["id"],),
    ).fetchone()

    return {
        "ok": True,
        "account": {
            "id": row["id"],
            "name": row["name"],
            "account_type": row["account_type"],
            "active": bool(row["active"]),
            "asset_class": row["asset_class"],
            "apr": float(row["apr"]) if row["apr"] is not None else None,
            "min_payment": float(row["min_payment"]) if row["min_payment"] is not None else None,
            "expense_ratio_pct": float(row["expense_ratio_pct"]) if row["expense_ratio_pct"] is not None else None,
            "annual_fee": float(row["annual_fee"]) if row["annual_fee"] is not None else None,
            "balance": float(bal_row["balance"]) if bal_row else None,
            "balance_as_of": bal_row["as_of_date"] if bal_row else None,
        },
    }


@router.get("/{name}/balances")
def get_account_balances(
    name: str,
    since: str | None = Query(None, description="YYYY-MM-DD"),
    conn: sqlite3.Connection = Depends(get_db),
):
    row = conn.execute("SELECT id FROM accounts WHERE name = ?", (name,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Account '{name}' not found")

    since_date = date.fromisoformat(since) if since else date(2000, 1, 1)
    balances = conn.execute(
        "SELECT as_of_date, balance FROM balance_history "
        "WHERE account_id = ? AND as_of_date >= ? ORDER BY as_of_date",
        (row["id"], since_date.isoformat()),
    ).fetchall()

    return {
        "ok": True,
        "account": name,
        "balances": [
            {"date": b["as_of_date"], "balance": float(b["balance"])}
            for b in balances
        ],
    }
