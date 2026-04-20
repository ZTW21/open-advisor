"""Tax pack endpoint."""

from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends

from finance_advisor.analytics import tax_pack
from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/taxpack", tags=["taxpack"])


@router.get("/{year}")
def get_taxpack(
    year: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    result = tax_pack(conn, year)
    return {"ok": True, **result}
