"""Tests for `finance_advisor.categorize_engine`.

These tests build rules on the fly (via the categorize CLI) and then verify
the matching engine picks the right rule for a variety of merchant strings
and filter combinations.
"""

from __future__ import annotations

from finance_advisor.categorize_engine import classify, load_rules
from finance_advisor.db import connect


def _mk_rules(invoke):
    """Create a small rule set; return the initialized invoke."""
    invoke("init")
    invoke("account", "add", "--name", "chase", "--institution", "Chase", "--type", "checking")
    invoke("account", "add", "--name", "ally", "--institution", "Ally", "--type", "savings")
    invoke("categorize", "category", "add", "--name", "Groceries")
    invoke("categorize", "category", "add", "--name", "Coffee")
    invoke("categorize", "category", "add", "--name", "Income", "--is-income")
    invoke("categorize", "category", "add", "--name", "ChaseOnly")

    invoke("categorize", "rule", "add", "--match", "WHOLE FOODS", "--category", "Groceries")
    invoke("categorize", "rule", "add", "--match", "STARBUCKS", "--category", "Coffee")
    invoke("categorize", "rule", "add", "--match", "PAYROLL", "--category", "Income",
           "--amount-filter", ">0")
    # Higher priority rule takes precedence over the default Coffee rule.
    invoke("categorize", "rule", "add", "--match", "STARBUCKS PIKE",
           "--category", "Groceries", "--priority", "200")
    # Account-scoped rule.
    invoke("categorize", "rule", "add", "--match", "ANY",
           "--category", "ChaseOnly", "--account", "chase", "--priority", "50")
    return invoke


def _category_id(conn, name: str) -> int:
    return conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()["id"]


def test_substring_match(db_path, invoke) -> None:
    _mk_rules(invoke)
    conn = connect(db_path)
    try:
        rules = load_rules(conn)
        hit = classify(rules, account_name="chase", normalized_desc="WHOLE FOODS MKT", amount=-30.0)
        assert hit is not None
        assert hit[0] == _category_id(conn, "Groceries")
    finally:
        conn.close()


def test_priority_wins(db_path, invoke) -> None:
    """The priority-200 'STARBUCKS PIKE' rule beats the priority-100 'STARBUCKS' rule."""
    _mk_rules(invoke)
    conn = connect(db_path)
    try:
        rules = load_rules(conn)
        hit = classify(rules, account_name="chase",
                       normalized_desc="STARBUCKS PIKE ROAST", amount=-5.0)
        assert hit is not None
        assert hit[0] == _category_id(conn, "Groceries")

        hit = classify(rules, account_name="chase",
                       normalized_desc="STARBUCKS STORE", amount=-5.0)
        assert hit is not None
        assert hit[0] == _category_id(conn, "Coffee")
    finally:
        conn.close()


def test_amount_filter(db_path, invoke) -> None:
    """A rule scoped to `>0` should not match negative amounts."""
    _mk_rules(invoke)
    conn = connect(db_path)
    try:
        rules = load_rules(conn)
        # Positive — should match PAYROLL → Income.
        hit = classify(rules, account_name="chase",
                       normalized_desc="PAYROLL ACME", amount=3200.0)
        assert hit is not None
        assert hit[0] == _category_id(conn, "Income")

        # Negative PAYROLL (e.g., a refund) — amount filter blocks the rule.
        hit = classify(rules, account_name="chase",
                       normalized_desc="PAYROLL ACME", amount=-100.0)
        assert hit is None
    finally:
        conn.close()


def test_account_filter(db_path, invoke) -> None:
    """Account-scoped rule only fires on the named account."""
    _mk_rules(invoke)
    conn = connect(db_path)
    try:
        rules = load_rules(conn)
        hit = classify(rules, account_name="chase",
                       normalized_desc="ANY MERCHANT", amount=-1.0)
        assert hit is not None
        assert hit[0] == _category_id(conn, "ChaseOnly")

        hit = classify(rules, account_name="ally",
                       normalized_desc="ANY MERCHANT", amount=-1.0)
        assert hit is None
    finally:
        conn.close()


def test_no_match_returns_none(db_path, invoke) -> None:
    _mk_rules(invoke)
    conn = connect(db_path)
    try:
        rules = load_rules(conn)
        hit = classify(rules, account_name="chase",
                       normalized_desc="MYSTERY MERCHANT", amount=-5.0)
        assert hit is None
    finally:
        conn.close()
