"""Mode detection endpoint."""

from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, Query

from finance_advisor.analytics import mode_detect
from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/mode", tags=["mode"])


@router.get("")
def get_mode(
    as_of: str | None = Query(None, description="YYYY-MM-DD, default today"),
    conn: sqlite3.Connection = Depends(get_db),
):
    target = date.fromisoformat(as_of) if as_of else date.today()
    result = mode_detect(conn, target)
    return {"ok": True, **result}
