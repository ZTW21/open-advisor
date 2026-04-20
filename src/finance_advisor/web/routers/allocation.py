"""Allocation and drift endpoints."""

from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, Query

from finance_advisor.analytics import allocation_targets, current_allocation
from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/allocation", tags=["allocation"])


@router.get("")
def get_allocation(
    as_of: str | None = Query(None, description="YYYY-MM-DD, default today"),
    conn: sqlite3.Connection = Depends(get_db),
):
    target = date.fromisoformat(as_of) if as_of else date.today()
    alloc = current_allocation(conn, target)
    targets = allocation_targets(conn, target)

    # Compute drift
    targets_map = targets["targets"]
    current_map = {c["asset_class"]: c for c in alloc["by_class"]}
    drift_rows = []
    for ac in sorted(set(current_map.keys()) | set(targets_map.keys())):
        cur_pct = current_map[ac]["pct"] if ac in current_map else 0.0
        tgt_pct = targets_map.get(ac)
        drift_rows.append({
            "asset_class": ac,
            "current_pct": cur_pct,
            "target_pct": tgt_pct,
            "drift_pp": round(cur_pct - tgt_pct, 2) if tgt_pct is not None else None,
        })

    return {
        "ok": True,
        "as_of": target.isoformat(),
        "assets_total": alloc["assets_total"],
        "by_class": alloc["by_class"],
        "targets": targets_map,
        "targets_set": bool(targets_map),
        "drift": drift_rows,
        "missing_balance": alloc["missing_balance"],
    }
