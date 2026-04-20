"""Goal progress endpoints."""

from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from finance_advisor.analytics import goal_progress
from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/goals", tags=["goals"])


@router.get("")
def get_goals(
    as_of: str | None = Query(None, description="YYYY-MM-DD, default today"),
    conn: sqlite3.Connection = Depends(get_db),
):
    target = date.fromisoformat(as_of) if as_of else date.today()
    goals = goal_progress(conn, target)
    return {"ok": True, "as_of": target.isoformat(), "goals": goals}


@router.get("/{goal_id}/history")
def get_goal_history(
    goal_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    goal = conn.execute(
        "SELECT id, name FROM goals WHERE id = ?", (goal_id,)
    ).fetchone()
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")

    rows = conn.execute(
        "SELECT as_of_date, amount FROM goals_progress "
        "WHERE goal_id = ? ORDER BY as_of_date",
        (goal_id,),
    ).fetchall()

    return {
        "ok": True,
        "goal_id": goal_id,
        "name": goal["name"],
        "history": [
            {"date": r["as_of_date"], "amount": float(r["amount"])}
            for r in rows
        ],
    }
