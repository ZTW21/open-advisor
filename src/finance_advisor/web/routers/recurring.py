"""Recurring charges endpoint."""

from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, Query

from finance_advisor.analytics import detect_recurring
from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/recurring", tags=["recurring"])


@router.get("")
def get_recurring(
    lookback_months: int = Query(6, ge=3, le=24),
    conn: sqlite3.Connection = Depends(get_db),
):
    result = detect_recurring(conn, date.today(), lookback_months=lookback_months)
    return {
        "ok": True,
        "lookback_months": lookback_months,
        "recurring": result,
        "count": len(result),
        "total_estimated_annual": sum(r["estimated_annual"] for r in result),
    }
