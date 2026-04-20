"""Tests for the advisor insights system."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from finance_advisor.db import apply_migrations, connect
from finance_advisor.insights import generate_insights, sync_insights


# ---------- fixtures ----------

@pytest.fixture
def conn(tmp_path):
    """Fresh DB with migrations applied."""
    db_path = tmp_path / "finance.sqlite"
    c = connect(db_path)
    apply_migrations(c)
    return c


def _add_account(conn, name, account_type, *, apr=None, min_payment=None):
    conn.execute(
        "INSERT INTO accounts (name, account_type, apr, min_payment) "
        "VALUES (?, ?, ?, ?)",
        (name, account_type, apr, min_payment),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM accounts WHERE name = ?", (name,)
    ).fetchone()["id"]


def _add_balance(conn, account_id, as_of, balance):
    conn.execute(
        "INSERT OR REPLACE INTO balance_history (account_id, as_of_date, balance) "
        "VALUES (?, ?, ?)",
        (account_id, as_of, balance),
    )
    conn.commit()


def _add_transaction(conn, account_id, dt, amount, desc, *, dedup_key=None):
    key = dedup_key or f"{account_id}|{dt}|{amount}|{desc}"
    conn.execute(
        "INSERT INTO transactions "
        "(account_id, date, amount, description_raw, merchant_normalized, dedup_key) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (account_id, dt, amount, desc, desc.upper(), key),
    )
    conn.commit()


# ---------- tests: empty DB ----------

class TestEmptyDB:
    def test_generates_stale_data_insight_on_empty(self, conn):
        insights = generate_insights(conn, date.today())
        keys = [i["insight_key"] for i in insights]
        assert "stale_data:no_transactions" in keys

    def test_no_crash_on_empty_db(self, conn):
        """generate_insights should not crash even with zero data."""
        insights = generate_insights(conn, date.today())
        assert isinstance(insights, list)

    def test_sync_creates_table_and_persists(self, conn):
        raw = generate_insights(conn, date.today())
        active = sync_insights(conn, raw)
        assert len(active) > 0
        # Verify persisted
        row = conn.execute("SELECT COUNT(*) AS n FROM insights").fetchone()
        assert row["n"] > 0


# ---------- tests: debt insights ----------

class TestDebtInsights:
    def test_high_apr_debt_flagged(self, conn):
        today = date.today()
        aid = _add_account(conn, "bad_card", "credit_card", apr=24.99)
        _add_balance(conn, aid, today.isoformat(), 5000)

        insights = generate_insights(conn, today)
        debt_insights = [i for i in insights if i["insight_key"] == "debt_interest:bad_card"]
        assert len(debt_insights) == 1
        assert debt_insights[0]["severity"] == "alert"
        assert "$104" in debt_insights[0]["title"]  # ~5000 * 24.99% / 12

    def test_low_apr_debt_not_flagged(self, conn):
        today = date.today()
        aid = _add_account(conn, "mortgage", "mortgage", apr=3.5)
        _add_balance(conn, aid, today.isoformat(), 200000)

        insights = generate_insights(conn, today)
        debt_keys = [i["insight_key"] for i in insights if i["type"] == "debt"]
        assert len(debt_keys) == 0


# ---------- tests: emergency fund ----------

class TestEmergencyFund:
    def test_critical_emergency_fund(self, conn):
        today = date.today()
        # Checking with $500
        checking_id = _add_account(conn, "checking", "checking")
        _add_balance(conn, checking_id, today.isoformat(), 500)
        # Transactions to establish outflow (~$3000/month)
        for i in range(3):
            month_ago = today - timedelta(days=30 + i * 30)
            _add_transaction(
                conn, checking_id,
                month_ago.isoformat(), -3000, f"rent_{i}",
            )

        insights = generate_insights(conn, today)
        ef = [i for i in insights if i["source"] == "emergency_fund"]
        assert len(ef) == 1
        assert ef[0]["severity"] == "alert"

    def test_strong_emergency_fund(self, conn):
        today = date.today()
        checking_id = _add_account(conn, "checking", "checking")
        _add_balance(conn, checking_id, today.isoformat(), 30000)
        for i in range(3):
            month_ago = today - timedelta(days=30 + i * 30)
            _add_transaction(
                conn, checking_id,
                month_ago.isoformat(), -3000, f"rent_{i}",
            )

        insights = generate_insights(conn, today)
        ef = [i for i in insights if i["source"] == "emergency_fund"]
        assert len(ef) == 1
        assert ef[0]["severity"] == "positive"


# ---------- tests: savings rate ----------

class TestSavingsRate:
    def test_negative_savings_rate(self, conn):
        today = date.today()
        aid = _add_account(conn, "checking", "checking")
        _add_balance(conn, aid, today.isoformat(), 5000)
        # Income: $2000, Spending: $4000 in last 30 days
        cat_id = conn.execute(
            "INSERT INTO categories (name, is_income) VALUES ('salary', 1)"
        ).lastrowid
        conn.commit()
        _add_transaction(conn, aid, today.isoformat(), 2000, "paycheck")
        conn.execute(
            "UPDATE transactions SET category_id = ? WHERE description_raw = 'paycheck'",
            (cat_id,),
        )
        conn.commit()
        for i in range(4):
            dt = (today - timedelta(days=i * 7)).isoformat()
            _add_transaction(conn, aid, dt, -1000, f"expense_{i}")

        insights = generate_insights(conn, today)
        sr = [i for i in insights if i["source"] == "savings_rate"]
        assert len(sr) == 1
        assert sr[0]["severity"] == "alert"

    def test_strong_savings_rate(self, conn):
        today = date.today()
        aid = _add_account(conn, "checking", "checking")
        _add_balance(conn, aid, today.isoformat(), 10000)
        cat_id = conn.execute(
            "INSERT INTO categories (name, is_income) VALUES ('salary', 1)"
        ).lastrowid
        conn.commit()
        _add_transaction(conn, aid, today.isoformat(), 10000, "paycheck")
        conn.execute(
            "UPDATE transactions SET category_id = ? WHERE description_raw = 'paycheck'",
            (cat_id,),
        )
        conn.commit()
        _add_transaction(conn, aid, today.isoformat(), -2000, "expenses")

        insights = generate_insights(conn, today)
        sr = [i for i in insights if i["source"] == "savings_rate"]
        assert len(sr) == 1
        assert sr[0]["severity"] == "positive"


# ---------- tests: stale data ----------

class TestStaleData:
    def test_no_transactions_flagged(self, conn):
        insights = generate_insights(conn, date.today())
        stale = [i for i in insights if i["source"] == "stale_data"]
        assert len(stale) == 1
        assert stale[0]["insight_key"] == "stale_data:no_transactions"

    def test_old_data_flagged(self, conn):
        today = date.today()
        aid = _add_account(conn, "checking", "checking")
        old_date = (today - timedelta(days=20)).isoformat()
        _add_transaction(conn, aid, old_date, -50, "old_purchase")

        insights = generate_insights(conn, today)
        stale = [i for i in insights if i["source"] == "stale_data"]
        assert len(stale) == 1
        assert "20 days old" in stale[0]["title"]

    def test_fresh_data_not_flagged(self, conn):
        today = date.today()
        aid = _add_account(conn, "checking", "checking")
        _add_transaction(conn, aid, today.isoformat(), -50, "recent_purchase")

        insights = generate_insights(conn, today)
        stale = [i for i in insights if i["source"] == "stale_data"]
        assert len(stale) == 0


# ---------- tests: net worth trend ----------

class TestNetWorthTrend:
    def test_positive_trend(self, conn):
        today = date.today()
        aid = _add_account(conn, "savings", "savings")
        month_ago = (today - timedelta(days=30)).isoformat()
        _add_balance(conn, aid, month_ago, 10000)
        _add_balance(conn, aid, today.isoformat(), 12000)

        insights = generate_insights(conn, today)
        nw = [i for i in insights if i["source"] == "networth_trend"]
        assert len(nw) == 1
        assert nw[0]["severity"] == "positive"
        assert "$2,000" in nw[0]["title"]

    def test_negative_trend(self, conn):
        today = date.today()
        aid = _add_account(conn, "savings", "savings")
        month_ago = (today - timedelta(days=30)).isoformat()
        _add_balance(conn, aid, month_ago, 10000)
        _add_balance(conn, aid, today.isoformat(), 8000)

        insights = generate_insights(conn, today)
        nw = [i for i in insights if i["source"] == "networth_trend"]
        assert len(nw) == 1
        assert nw[0]["severity"] in ("info", "warn")


# ---------- tests: sync lifecycle ----------

class TestSyncInsights:
    def test_sync_persists_and_returns(self, conn):
        raw = generate_insights(conn, date.today())
        active = sync_insights(conn, raw)
        assert isinstance(active, list)
        for ins in active:
            assert "id" in ins
            assert "title" in ins

    def test_dismiss_removes_from_active(self, conn):
        raw = generate_insights(conn, date.today())
        active = sync_insights(conn, raw)
        assert len(active) > 0

        # Dismiss the first one
        first_id = active[0]["id"]
        conn.execute(
            "UPDATE insights SET dismissed_at = datetime('now') WHERE id = ?",
            (first_id,),
        )
        conn.commit()

        # Re-sync — should have one fewer
        raw2 = generate_insights(conn, date.today())
        active2 = sync_insights(conn, raw2)
        assert len(active2) == len(active) - 1

    def test_stale_conditions_cleared(self, conn):
        today = date.today()

        # First sync: no transactions → stale_data insight
        raw = generate_insights(conn, today)
        active = sync_insights(conn, raw)
        stale_keys = [i["insight_key"] for i in active if i["source"] == "stale_data"]
        assert "stale_data:no_transactions" in stale_keys

        # Add a transaction so data is no longer stale
        aid = _add_account(conn, "checking", "checking")
        _add_transaction(conn, aid, today.isoformat(), -50, "purchase")

        # Re-sync: stale_data insight should be cleared
        raw2 = generate_insights(conn, today)
        active2 = sync_insights(conn, raw2)
        stale_keys2 = [i["insight_key"] for i in active2 if i["source"] == "stale_data"]
        assert "stale_data:no_transactions" not in stale_keys2

    def test_updated_insights_reflect_new_data(self, conn):
        today = date.today()
        aid = _add_account(conn, "bad_card", "credit_card", apr=24.99)
        _add_balance(conn, aid, today.isoformat(), 5000)

        raw = generate_insights(conn, today)
        active = sync_insights(conn, raw)
        debt = [i for i in active if i["insight_key"] == "debt_interest:bad_card"]
        assert len(debt) == 1
        original_title = debt[0]["title"]

        # Pay down to $2000
        _add_balance(conn, aid, today.isoformat(), 2000)

        raw2 = generate_insights(conn, today)
        active2 = sync_insights(conn, raw2)
        debt2 = [i for i in active2 if i["insight_key"] == "debt_interest:bad_card"]
        assert len(debt2) == 1
        # Title should change because monthly cost changed
        assert debt2[0]["title"] != original_title


# ---------- tests: goals ----------

class TestGoalInsights:
    def test_goal_behind_pace(self, conn):
        today = date.today()
        conn.execute(
            "INSERT INTO goals (name, target_amount, target_date, priority, status) "
            "VALUES ('down_payment', 50000, ?, 1, 'active')",
            ((today + timedelta(days=365)).isoformat(),),
        )
        conn.commit()
        goal_id = conn.execute("SELECT id FROM goals WHERE name='down_payment'").fetchone()["id"]
        # Start date 6 months ago, but only $5k saved
        start = today - timedelta(days=180)
        conn.execute(
            "INSERT INTO goals_progress (goal_id, as_of_date, amount) VALUES (?, ?, ?)",
            (goal_id, start.isoformat(), 0),
        )
        conn.execute(
            "INSERT INTO goals_progress (goal_id, as_of_date, amount) VALUES (?, ?, ?)",
            (goal_id, today.isoformat(), 5000),
        )
        conn.commit()

        insights = generate_insights(conn, today)
        goal_ins = [i for i in insights if i["source"] == "goal_pace"]
        assert len(goal_ins) == 1
        assert goal_ins[0]["severity"] == "warn"

    def test_goal_milestone(self, conn):
        today = date.today()
        conn.execute(
            "INSERT INTO goals (name, target_amount, target_date, priority, status) "
            "VALUES ('vacation', 10000, ?, 1, 'active')",
            ((today + timedelta(days=365)).isoformat(),),
        )
        conn.commit()
        goal_id = conn.execute("SELECT id FROM goals WHERE name='vacation'").fetchone()["id"]
        start = today - timedelta(days=90)
        conn.execute(
            "INSERT INTO goals_progress (goal_id, as_of_date, amount) VALUES (?, ?, ?)",
            (goal_id, start.isoformat(), 0),
        )
        conn.execute(
            "INSERT INTO goals_progress (goal_id, as_of_date, amount) VALUES (?, ?, ?)",
            (goal_id, today.isoformat(), 6000),
        )
        conn.commit()

        insights = generate_insights(conn, today)
        milestones = [i for i in insights if i["source"] == "goal_milestone"]
        assert len(milestones) == 1
        assert milestones[0]["severity"] == "positive"
        assert ":50" in milestones[0]["insight_key"]


# ---------- tests: allocation drift ----------

class TestAllocationDrift:
    def test_drift_flagged(self, conn):
        today = date.today()
        # Set up allocation target: 60% stocks, 40% bonds
        conn.execute(
            "INSERT INTO allocation_targets (asset_class, target_pct, active_from) "
            "VALUES ('us_stocks', 60, ?)",
            (today.isoformat(),),
        )
        conn.execute(
            "INSERT INTO allocation_targets (asset_class, target_pct, active_from) "
            "VALUES ('bonds', 40, ?)",
            (today.isoformat(),),
        )
        conn.commit()

        # Actual: 80% stocks ($80k), 20% bonds ($20k)
        stock_id = _add_account(conn, "brokerage", "brokerage")
        conn.execute(
            "UPDATE accounts SET asset_class = 'us_stocks' WHERE id = ?",
            (stock_id,),
        )
        bond_id = _add_account(conn, "bond_fund", "brokerage")
        conn.execute(
            "UPDATE accounts SET asset_class = 'bonds' WHERE id = ?",
            (bond_id,),
        )
        conn.commit()
        _add_balance(conn, stock_id, today.isoformat(), 80000)
        _add_balance(conn, bond_id, today.isoformat(), 20000)

        insights = generate_insights(conn, today)
        drift = [i for i in insights if i["source"] == "allocation_drift"]
        assert len(drift) == 2  # stocks overweight + bonds underweight
        severities = {i["severity"] for i in drift}
        assert "warn" in severities or "info" in severities
