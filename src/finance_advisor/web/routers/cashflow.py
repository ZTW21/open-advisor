"""Cashflow endpoints."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from finance_advisor.analytics import cashflow_by, cashflow_totals, parse_window
from finance_advisor.web.serialization import bucket_to_dict
from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/cashflow", tags=["cashflow"])


@router.get("")
def get_cashflow(
    window: str = Query("30d", description="Window spec, e.g. 7d, 30d, 3m"),
    by: str = Query("category", description="category | account | merchant"),
    conn: sqlite3.Connection = Depends(get_db),
):
    start, end = parse_window(window)
    totals = cashflow_totals(conn, start, end)
    buckets = cashflow_by(conn, start, end, by=by)
    return {
        "ok": True,
        "window": window,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "totals": totals,
        "by": by,
        "buckets": [bucket_to_dict(b) for b in buckets],
    }
