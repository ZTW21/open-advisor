"""Tests for the database schema: migrations create the tables we expect."""

from __future__ import annotations

from pathlib import Path

from finance_advisor.db import apply_migrations, connect, current_schema_version


EXPECTED_TABLES = {
    "schema_version",
    "accounts",
    "balance_history",
    "categories",
    "imports",
    "transactions",
    "holdings",
    "categorization_rules",
    "budget_plan",
    "goals",
    "goals_progress",
    "recurring",
}


def _tables(conn) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {r["name"] for r in rows}


def test_migrations_create_all_expected_tables(db_path: Path) -> None:
    conn = connect(db_path)
    try:
        apply_migrations(conn)
        tables = _tables(conn)
    finally:
        conn.close()
    missing = EXPECTED_TABLES - tables
    assert not missing, f"Missing tables after migrations: {sorted(missing)}"


def test_migrations_record_version(db_path: Path) -> None:
    conn = connect(db_path)
    try:
        applied = apply_migrations(conn)
        version = current_schema_version(conn)
    finally:
        conn.close()
    # Every shipped migration should be applied on a fresh DB; the exact
    # highest version is whatever's in migrations/, so assert monotonicity
    # rather than a fixed number (which rots every phase).
    assert applied == sorted(applied)
    assert applied[0] == 1
    assert version == applied[-1]


def test_migrations_are_idempotent(db_path: Path) -> None:
    conn = connect(db_path)
    try:
        first = apply_migrations(conn)
        second = apply_migrations(conn)
    finally:
        conn.close()
    assert first[0] == 1
    assert first == sorted(first)
    assert second == []


def test_transactions_dedup_key_unique(db_path: Path) -> None:
    """The dedup_key column must enforce uniqueness."""
    import sqlite3

    conn = connect(db_path)
    try:
        apply_migrations(conn)
        conn.execute(
            "INSERT INTO accounts (name, institution, account_type, currency, active) "
            "VALUES ('x', 'Bank', 'checking', 'USD', 1)"
        )
        acct_id = conn.execute("SELECT id FROM accounts WHERE name='x'").fetchone()["id"]
        conn.execute(
            "INSERT INTO transactions (account_id, date, amount, description_raw, dedup_key) "
            "VALUES (?, '2026-01-01', -10.00, 'coffee', 'k1')",
            (acct_id,),
        )
        conn.commit()
        try:
            conn.execute(
                "INSERT INTO transactions (account_id, date, amount, description_raw, dedup_key) "
                "VALUES (?, '2026-01-01', -10.00, 'coffee', 'k1')",
                (acct_id,),
            )
            conn.commit()
            raised = False
        except sqlite3.IntegrityError:
            raised = True
        assert raised, "Duplicate dedup_key should have raised IntegrityError"
    finally:
        conn.close()
