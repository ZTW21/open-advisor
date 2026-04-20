"""Integration tests for the web dashboard API."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from finance_advisor.db import apply_migrations, connect
from finance_advisor.web import deps
from finance_advisor.web.server import create_app


@pytest.fixture
def app(initialized_db, finance_dir):
    """Create a FastAPI test app pointing at the test DB."""
    app = create_app(str(initialized_db))
    return app


@pytest.fixture
def client(app):
    from starlette.testclient import TestClient

    return TestClient(app)


def _seed_accounts(db_path: Path):
    """Insert test accounts and balances."""
    conn = connect(db_path)
    try:
        conn.execute(
            "INSERT INTO accounts (name, account_type, active) VALUES (?, ?, ?)",
            ("Checking", "checking", 1),
        )
        conn.execute(
            "INSERT INTO accounts (name, account_type, active) VALUES (?, ?, ?)",
            ("Savings", "savings", 1),
        )
        conn.execute(
            "INSERT INTO accounts (name, account_type, active, apr, min_payment) "
            "VALUES (?, ?, ?, ?, ?)",
            ("Chase Card", "credit_card", 1, 24.99, 35.0),
        )
        conn.execute(
            "INSERT INTO balance_history (account_id, as_of_date, balance) VALUES (?, ?, ?)",
            (1, "2026-04-01", 5000.00),
        )
        conn.execute(
            "INSERT INTO balance_history (account_id, as_of_date, balance) VALUES (?, ?, ?)",
            (2, "2026-04-01", 15000.00),
        )
        conn.execute(
            "INSERT INTO balance_history (account_id, as_of_date, balance) VALUES (?, ?, ?)",
            (3, "2026-04-01", 2500.00),
        )
        conn.commit()
    finally:
        conn.close()


def _seed_transactions(db_path: Path):
    """Insert test transactions."""
    conn = connect(db_path)
    try:
        # Income category
        conn.execute(
            "INSERT INTO categories (name, is_income) VALUES (?, ?)", ("Salary", 1)
        )
        # Expense category
        conn.execute(
            "INSERT INTO categories (name) VALUES (?)", ("Groceries",)
        )
        conn.execute(
            "INSERT INTO categories (name) VALUES (?)", ("Dining",)
        )
        # Transactions (dedup_key is NOT NULL UNIQUE)
        conn.execute(
            "INSERT INTO transactions (account_id, date, amount, description_raw, "
            "merchant_normalized, category_id, dedup_key) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "2026-04-10", 5000.00, "ACME CORP PAYROLL", "Acme Corp", 1, "t1"),
        )
        conn.execute(
            "INSERT INTO transactions (account_id, date, amount, description_raw, "
            "merchant_normalized, category_id, dedup_key) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "2026-04-11", -85.50, "WHOLE FOODS #1234", "Whole Foods", 2, "t2"),
        )
        conn.execute(
            "INSERT INTO transactions (account_id, date, amount, description_raw, "
            "merchant_normalized, category_id, dedup_key) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "2026-04-12", -42.00, "PIZZA PLACE", "Pizza Place", 3, "t3"),
        )
        conn.execute(
            "INSERT INTO transactions (account_id, date, amount, description_raw, "
            "merchant_normalized, dedup_key) VALUES (?, ?, ?, ?, ?, ?)",
            (1, "2026-04-13", -15.00, "COFFEE SHOP", "Coffee Shop", "t4"),
        )
        conn.commit()
    finally:
        conn.close()


# ---------- empty DB tests ----------


class TestEmptyDB:
    def test_networth_empty(self, client):
        r = client.get("/api/networth")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["net_worth"] == 0.0

    def test_dashboard_empty(self, client):
        r = client.get("/api/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["net_worth"]["total"] == 0.0
        assert data["mode"]["mode"] == "balanced"

    def test_accounts_empty(self, client):
        r = client.get("/api/accounts")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["accounts"] == []
        assert data["count"] == 0

    def test_anomalies_empty(self, client):
        r = client.get("/api/anomalies")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["anomalies"] == []

    def test_mode_empty(self, client):
        r = client.get("/api/mode")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["mode"] in ("debt", "invest", "balanced")

    def test_cashflow_empty(self, client):
        r = client.get("/api/cashflow")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["totals"]["count"] == 0

    def test_transactions_empty(self, client):
        r = client.get("/api/transactions")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["transactions"] == []

    def test_goals_empty(self, client):
        r = client.get("/api/goals")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["goals"] == []

    def test_debt_empty(self, client):
        r = client.get("/api/debt")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["debts"] == []

    def test_categories_empty(self, client):
        r = client.get("/api/categories")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

    def test_networth_history_empty(self, client):
        r = client.get("/api/networth/history?months=6")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert len(data["history"]) == 6


# ---------- seeded DB tests ----------


class TestSeededDB:
    @pytest.fixture(autouse=True)
    def seed(self, initialized_db):
        _seed_accounts(initialized_db)
        _seed_transactions(initialized_db)

    def test_networth_seeded(self, client):
        r = client.get("/api/networth?as_of=2026-04-15")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        # 5000 + 15000 - 2500 = 17500
        assert data["net_worth"] == 17500.0
        assert data["assets_total"] == 20000.0
        assert data["liabilities_total"] == 2500.0
        assert len(data["breakdown"]) == 3

    def test_dashboard_seeded(self, client):
        r = client.get("/api/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["net_worth"]["total"] == 17500.0
        assert data["mode"]["mode"] == "debt"  # Chase card at 24.99%

    def test_accounts_list(self, client):
        r = client.get("/api/accounts")
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 3
        names = [a["name"] for a in data["accounts"]]
        assert "Checking" in names
        assert "Chase Card" in names

    def test_account_detail(self, client):
        r = client.get("/api/accounts/Checking")
        assert r.status_code == 200
        data = r.json()
        assert data["account"]["balance"] == 5000.0

    def test_account_not_found(self, client):
        r = client.get("/api/accounts/Nonexistent")
        assert r.status_code == 404

    def test_account_balances(self, client):
        r = client.get("/api/accounts/Checking/balances")
        assert r.status_code == 200
        data = r.json()
        assert len(data["balances"]) == 1
        assert data["balances"][0]["balance"] == 5000.0

    def test_cashflow_seeded(self, client):
        r = client.get("/api/cashflow?window=30d&by=category")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["totals"]["count"] > 0

    def test_transactions_list(self, client):
        r = client.get("/api/transactions")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 4
        assert len(data["transactions"]) == 4

    def test_transactions_filter_by_account(self, client):
        r = client.get("/api/transactions?account=Checking")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 4

    def test_transactions_search(self, client):
        r = client.get("/api/transactions?q=PIZZA")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1

    def test_uncategorized_transactions(self, client):
        r = client.get("/api/transactions/uncategorized")
        assert r.status_code == 200
        data = r.json()
        assert data["total_uncategorized"] == 1
        assert data["transactions"][0]["description"] == "COFFEE SHOP"

    def test_debt_roster(self, client):
        r = client.get("/api/debt?as_of=2026-04-15")
        assert r.status_code == 200
        data = r.json()
        assert len(data["debts"]) == 1
        assert data["debts"][0]["name"] == "Chase Card"
        assert data["debts"][0]["balance"] == 2500.0
        assert data["total"] == 2500.0

    def test_debt_simulate(self, client):
        r = client.post(
            "/api/debt/simulate?as_of=2026-04-15",
            json={"strategy": "avalanche", "extra_monthly": 100.0},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["converged"] is True
        assert data["months"] > 0

    def test_mode_seeded(self, client):
        r = client.get("/api/mode?as_of=2026-04-15")
        assert r.status_code == 200
        data = r.json()
        assert data["mode"] == "debt"

    def test_allocation_seeded(self, client):
        r = client.get("/api/allocation?as_of=2026-04-15")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["assets_total"] == 20000.0

    def test_categories_with_data(self, client):
        r = client.get("/api/categories")
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 3

    def test_category_rules_empty(self, client):
        r = client.get("/api/categories/rules")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

    def test_reports_daily(self, client):
        r = client.get("/api/reports/daily?date=2026-04-12")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["date"] == "2026-04-12"

    def test_reports_monthly(self, client):
        r = client.get("/api/reports/monthly?month=2026-04")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["month"] == "2026-04"

    def test_afford_check(self, client):
        r = client.post(
            "/api/afford",
            json={"amount": 1000.0, "min_months": 3.0, "as_of": "2026-04-15"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["verdict"] in ("green", "yellow", "red")
        assert data["liquid_cash_before"] == 20000.0

    def test_fees_empty(self, client):
        r = client.get("/api/fees?as_of=2026-04-15")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

    def test_recurring_empty(self, client):
        r = client.get("/api/recurring")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["recurring"] == []

    def test_imports_empty(self, client):
        r = client.get("/api/imports")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
