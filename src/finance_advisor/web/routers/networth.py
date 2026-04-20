"""Net worth endpoints."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from finance_advisor.analytics import networth_at
from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/networth", tags=["networth"])


@router.get("")
def get_networth(
    as_of: str | None = Query(None, description="YYYY-MM-DD, default today"),
    conn: sqlite3.Connection = Depends(get_db),
):
    target = date.fromisoformat(as_of) if as_of else date.today()
    result = networth_at(conn, target)
    return {"ok": True, **result}


@router.get("/history")
def get_networth_history(
    months: int = Query(12, ge=1, le=120),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Net worth at month-end for the last N months."""
    today = date.today()
    points = []
    for i in range(months):
        # Walk backwards: end of month i months ago
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        # Last day of that month
        if month == 12:
            end_of_month = date(year, 12, 31)
        else:
            end_of_month = date(year, month + 1, 1) - timedelta(days=1)
        nw = networth_at(conn, end_of_month)
        points.append({
            "date": end_of_month.isoformat(),
            "net_worth": nw["net_worth"],
            "assets": nw["assets_total"],
            "liabilities": nw["liabilities_total"],
        })
    points.reverse()
    return {"ok": True, "months": months, "history": points}
