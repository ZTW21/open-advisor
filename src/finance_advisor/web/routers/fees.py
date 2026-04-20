"""Fee audit endpoint."""

from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, Query

from finance_advisor.analytics import fee_audit
from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/fees", tags=["fees"])


@router.get("")
def get_fees(
    threshold_pct: float = Query(0.25),
    as_of: str | None = Query(None, description="YYYY-MM-DD, default today"),
    conn: sqlite3.Connection = Depends(get_db),
):
    target = date.fromisoformat(as_of) if as_of else date.today()
    result = fee_audit(conn, target, threshold_pct=threshold_pct)
    return {"ok": True, **result}
