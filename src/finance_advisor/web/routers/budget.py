"""Budget vs. actual endpoint."""

from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, Query

from finance_advisor.analytics import budget_vs_actual, parse_month
from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/budget", tags=["budget"])


@router.get("")
def get_budget(
    month: str | None = Query(None, description="YYYY-MM, default current month"),
    conn: sqlite3.Connection = Depends(get_db),
):
    if month:
        start, end = parse_month(month)
    else:
        today = date.today()
        month = f"{today.year:04d}-{today.month:02d}"
        start, end = parse_month(month)

    budgets = budget_vs_actual(conn, start, end)
    return {
        "ok": True,
        "month": month,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "budgets": budgets,
    }
