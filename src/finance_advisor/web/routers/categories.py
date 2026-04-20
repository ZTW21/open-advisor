"""Category endpoints (read-only)."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("")
def list_categories(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute(
        "SELECT id, name, parent_id, is_income, is_transfer "
        "FROM categories ORDER BY name"
    ).fetchall()

    categories = [
        {
            "id": r["id"],
            "name": r["name"],
            "parent_id": r["parent_id"],
            "is_income": bool(r["is_income"]) if r["is_income"] is not None else False,
            "is_transfer": bool(r["is_transfer"]) if r["is_transfer"] is not None else False,
        }
        for r in rows
    ]
    return {"ok": True, "categories": categories, "count": len(categories)}


@router.get("/rules")
def list_category_rules(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute(
        """
        SELECT cr.id, cr.match_pattern, cr.match_type,
               cr.category_id, c.name AS category_name,
               cr.priority, cr.account_filter, cr.amount_filter
        FROM categorization_rules cr
        JOIN categories c ON c.id = cr.category_id
        ORDER BY cr.priority DESC, c.name
        """
    ).fetchall()

    rules = [
        {
            "id": r["id"],
            "pattern": r["match_pattern"],
            "match_type": r["match_type"],
            "category_id": r["category_id"],
            "category_name": r["category_name"],
            "priority": r["priority"],
            "account_filter": r["account_filter"],
            "amount_filter": r["amount_filter"],
        }
        for r in rows
    ]
    return {"ok": True, "rules": rules, "count": len(rules)}
