"""Advisor insights API — persistent observations from the financial advisor."""

from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends

from finance_advisor.insights import generate_insights, sync_insights
from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("")
def get_insights(conn: sqlite3.Connection = Depends(get_db)):
    today = date.today()
    raw = generate_insights(conn, today)
    active = sync_insights(conn, raw)
    return {
        "ok": True,
        "as_of": today.isoformat(),
        "insights": active,
        "count": len(active),
    }


@router.post("/{insight_id}/dismiss")
def dismiss_insight(
    insight_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    row = conn.execute(
        "SELECT id FROM insights WHERE id = ?", (insight_id,)
    ).fetchone()
    if not row:
        return {"ok": False, "error": "insight_not_found"}

    conn.execute(
        "UPDATE insights SET dismissed_at = datetime('now') WHERE id = ?",
        (insight_id,),
    )
    conn.commit()
    return {"ok": True}
