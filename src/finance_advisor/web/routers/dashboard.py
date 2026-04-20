"""Composite dashboard endpoint — one request for the overview page."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from fastapi import APIRouter, Depends

from finance_advisor.analytics import (
    all_anomalies,
    budget_vs_actual,
    cashflow_totals,
    goal_progress,
    mode_detect,
    networth_at,
    parse_month,
    parse_window,
    savings_rate,
)
from finance_advisor.web.serialization import anomaly_to_dict
from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(conn: sqlite3.Connection = Depends(get_db)):
    today = date.today()

    # Net worth
    nw = networth_at(conn, today)

    # Mode
    md = mode_detect(conn, today)

    # Recent anomalies (last 7 days)
    anom_start, anom_end = parse_window("7d", today=today)
    anoms = all_anomalies(conn, anom_start, anom_end)

    # Cashflow last 30 days
    cf_start, cf_end = parse_window("30d", today=today)
    cf = cashflow_totals(conn, cf_start, cf_end)

    # Savings rate last 30 days
    sr = savings_rate(conn, cf_start, cf_end)

    # Goals
    goals = goal_progress(conn, today)

    # Budget vs. actual for current month
    month_label = f"{today.year:04d}-{today.month:02d}"
    month_start, month_end = parse_month(month_label)
    budgets = budget_vs_actual(conn, month_start, min(month_end, today))

    return {
        "ok": True,
        "as_of": today.isoformat(),
        "net_worth": {
            "total": nw["net_worth"],
            "assets": nw["assets_total"],
            "liabilities": nw["liabilities_total"],
            "oldest_balance_as_of": nw["oldest_balance_as_of"],
            "account_count": len(nw["breakdown"]),
        },
        "mode": {
            "mode": md["mode"],
            "reasons": md["reasons"],
        },
        "cashflow_30d": {
            "start": cf_start.isoformat(),
            "end": cf_end.isoformat(),
            **cf,
        },
        "savings_rate": sr,
        "goals": goals,
        "budget_vs_actual": budgets,
        "anomalies": [anomaly_to_dict(a) for a in anoms[:5]],
    }
