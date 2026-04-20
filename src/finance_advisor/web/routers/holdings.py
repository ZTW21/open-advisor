"""Holdings endpoint."""

from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, Query

from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/holdings", tags=["holdings"])


@router.get("")
def get_holdings(
    as_of: str | None = Query(None, description="YYYY-MM-DD, default today"),
    conn: sqlite3.Connection = Depends(get_db),
):
    target = date.fromisoformat(as_of) if as_of else date.today()

    # Latest holding per (account, ticker) on or before as_of
    rows = conn.execute(
        """
        SELECT h.account_id, a.name AS account_name, h.ticker, h.shares,
               h.cost_basis, h.as_of_date
        FROM holdings h
        JOIN accounts a ON a.id = h.account_id
        WHERE h.as_of_date <= ?
          AND h.as_of_date = (
              SELECT MAX(h2.as_of_date) FROM holdings h2
              WHERE h2.account_id = h.account_id
                AND h2.ticker = h.ticker
                AND h2.as_of_date <= ?
          )
        ORDER BY a.name, h.ticker
        """,
        (target.isoformat(), target.isoformat()),
    ).fetchall()

    return {
        "ok": True,
        "as_of": target.isoformat(),
        "holdings": [
            {
                "account": r["account_name"],
                "ticker": r["ticker"],
                "shares": float(r["shares"]),
                "cost_basis": float(r["cost_basis"]) if r["cost_basis"] else None,
                "as_of_date": r["as_of_date"],
            }
            for r in rows
        ],
    }
