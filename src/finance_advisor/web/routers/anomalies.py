"""Anomaly detection endpoint."""

from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, Query

from finance_advisor.analytics import all_anomalies, parse_window
from finance_advisor.web.serialization import anomaly_to_dict
from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])


@router.get("")
def get_anomalies(
    window: str = Query("30d", description="Window spec, e.g. 7d, 30d, 3m"),
    conn: sqlite3.Connection = Depends(get_db),
):
    start, end = parse_window(window)
    anoms = all_anomalies(conn, start, end)
    return {
        "ok": True,
        "window": window,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "anomalies": [anomaly_to_dict(a) for a in anoms],
        "count": len(anoms),
    }
