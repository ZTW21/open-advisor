"""Import history endpoint."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.get("")
def list_imports(
    limit: int = Query(50, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_db),
):
    rows = conn.execute(
        """
        SELECT id, source_file, file_checksum, imported_at,
               row_count, new_count, dup_count, flagged_count, status
        FROM imports
        ORDER BY imported_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    return {
        "ok": True,
        "imports": [
            {
                "id": r["id"],
                "source_file": r["source_file"],
                "file_checksum": r["file_checksum"],
                "imported_at": r["imported_at"],
                "row_count": r["row_count"],
                "new_count": r["new_count"],
                "dup_count": r["dup_count"],
                "flagged_count": r["flagged_count"],
                "status": r["status"],
            }
            for r in rows
        ],
    }
