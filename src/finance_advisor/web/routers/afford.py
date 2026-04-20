"""Affordability check endpoint."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from finance_advisor.analytics import (
    goal_pace_impact,
    liquid_cash,
    savings_rate,
    trailing_monthly_outflow,
)
from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/afford", tags=["afford"])


class AffordRequest(BaseModel):
    amount: float
    min_months: float = 3.0
    as_of: Optional[str] = None


@router.post("")
def check_afford(
    req: AffordRequest,
    conn: sqlite3.Connection = Depends(get_db),
):
    target = date.fromisoformat(req.as_of) if req.as_of else date.today()

    cash = liquid_cash(conn, target)
    outflow = trailing_monthly_outflow(conn, target)
    monthly_avg = outflow["monthly_average"]

    # Emergency fund months after the purchase
    remaining_cash = cash["total"] - req.amount
    ef_months_after = remaining_cash / monthly_avg if monthly_avg > 0 else None

    # Verdict
    if ef_months_after is not None and ef_months_after >= req.min_months:
        verdict = "green"
    elif ef_months_after is not None and ef_months_after >= req.min_months * 0.5:
        verdict = "yellow"
    else:
        verdict = "red"

    # Goal impact
    impact = goal_pace_impact(conn, target, reduction=req.amount)

    # Current savings rate for context
    from finance_advisor.analytics import parse_window
    sr_start, sr_end = parse_window("30d", today=target)
    sr = savings_rate(conn, sr_start, sr_end)

    return {
        "ok": True,
        "amount": req.amount,
        "as_of": target.isoformat(),
        "verdict": verdict,
        "liquid_cash_before": cash["total"],
        "liquid_cash_after": remaining_cash,
        "monthly_outflow_avg": monthly_avg,
        "emergency_months_after": round(ef_months_after, 1) if ef_months_after is not None else None,
        "min_months_required": req.min_months,
        "savings_rate": sr,
        "goal_impact": impact,
    }
