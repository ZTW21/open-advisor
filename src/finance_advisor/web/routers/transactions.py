"""Transaction endpoints (read-only)."""

from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, Query

from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("")
def list_transactions(
    account: str | None = Query(None),
    category: str | None = Query(None),
    since: str | None = Query(None, description="YYYY-MM-DD"),
    until: str | None = Query(None, description="YYYY-MM-DD"),
    q: str | None = Query(None, description="Search description"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
):
    conditions = []
    params: list = []

    if account:
        conditions.append("a.name = ?")
        params.append(account)
    if category:
        conditions.append("c.name = ?")
        params.append(category)
    if since:
        conditions.append("t.date >= ?")
        params.append(since)
    if until:
        conditions.append("t.date <= ?")
        params.append(until)
    if q:
        conditions.append("(t.description_raw LIKE ? OR t.merchant_normalized LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    rows = conn.execute(
        f"""
        SELECT t.id, t.date, t.amount, t.description_raw, t.merchant_normalized,
               a.name AS account_name, COALESCE(c.name, '') AS category_name,
               t.category_id, t.transfer_group_id
        FROM transactions t
        LEFT JOIN accounts a ON a.id = t.account_id
        LEFT JOIN categories c ON c.id = t.category_id
        {where}
        ORDER BY t.date DESC, t.id DESC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    ).fetchall()

    count_row = conn.execute(
        f"SELECT COUNT(*) AS n FROM transactions t "
        f"LEFT JOIN accounts a ON a.id = t.account_id "
        f"LEFT JOIN categories c ON c.id = t.category_id {where}",
        params,
    ).fetchone()

    return {
        "ok": True,
        "transactions": [
            {
                "id": r["id"],
                "date": r["date"],
                "amount": float(r["amount"]),
                "description": r["description_raw"],
                "merchant": r["merchant_normalized"],
                "account": r["account_name"],
                "category": r["category_name"],
                "is_transfer": bool(r["transfer_group_id"]),
            }
            for r in rows
        ],
        "total": count_row["n"],
        "limit": limit,
        "offset": offset,
    }


@router.get("/uncategorized")
def uncategorized_transactions(
    limit: int = Query(50, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_db),
):
    rows = conn.execute(
        """
        SELECT t.id, t.date, t.amount, t.description_raw, t.merchant_normalized,
               a.name AS account_name
        FROM transactions t
        LEFT JOIN accounts a ON a.id = t.account_id
        WHERE t.category_id IS NULL
        ORDER BY t.date DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    count_row = conn.execute(
        "SELECT COUNT(*) AS n FROM transactions WHERE category_id IS NULL"
    ).fetchone()

    return {
        "ok": True,
        "transactions": [
            {
                "id": r["id"],
                "date": r["date"],
                "amount": float(r["amount"]),
                "description": r["description_raw"],
                "merchant": r["merchant_normalized"],
                "account": r["account_name"],
            }
            for r in rows
        ],
        "total_uncategorized": count_row["n"],
    }
