"""Debt roster and payoff simulation endpoints."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from finance_advisor.analytics import debt_roster, simulate_payoff
from finance_advisor.web.serialization import debt_to_dict
from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/debt", tags=["debt"])


@router.get("")
def get_debt(
    as_of: str | None = Query(None, description="YYYY-MM-DD, default today"),
    conn: sqlite3.Connection = Depends(get_db),
):
    target = date.fromisoformat(as_of) if as_of else date.today()
    debts = debt_roster(conn, target)
    return {
        "ok": True,
        "as_of": target.isoformat(),
        "debts": [debt_to_dict(d) for d in debts],
        "total": sum(d.balance for d in debts),
    }


class SimulateRequest(BaseModel):
    strategy: str = "avalanche"
    extra_monthly: float = 0.0
    custom_order: Optional[list[str]] = None


@router.post("/simulate")
def simulate(
    req: SimulateRequest,
    as_of: str | None = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
):
    target = date.fromisoformat(as_of) if as_of else date.today()
    debts = debt_roster(conn, target)
    result = simulate_payoff(
        debts,
        strategy=req.strategy,
        extra_monthly=req.extra_monthly,
        custom_order=req.custom_order,
    )
    return {"ok": True, **result}
