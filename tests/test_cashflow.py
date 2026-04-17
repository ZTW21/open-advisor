"""Tests for `finance cashflow`."""

from __future__ import annotations

import json
from pathlib import Path


# ---------- fixture CSV ----------

CHASE_MIX = """Transaction Date,Post Date,Description,Category,Type,Amount
04/01/2026,04/01/2026,RENT PAYMENT,Bills,Sale,-1800.00
04/02/2026,04/02/2026,WHOLE FOODS MKT #10230,Groceries,Sale,-87.45
04/03/2026,04/03/2026,STARBUCKS STORE #1234,Food,Sale,-6.25
04/04/2026,04/04/2026,WHOLE FOODS MKT #10230,Groceries,Sale,-52.10
04/05/2026,04/05/2026,PAYROLL DEPOSIT ACME INC,Payment,Payment,3200.00
04/06/2026,04/06/2026,TRANSFER TO ALLY,Transfer,Payment,-500.00
"""

ALLY_IN = """Date,Description,Amount
04/06/2026,TRANSFER FROM CHASE CHECKING,500.00
04/10/2026,INTEREST EARNED,3.21
"""


def _seed_with_data(invoke, finance_dir: Path) -> None:
    invoke("init")
    invoke("account", "add", "--name", "chase", "--institution", "Chase", "--type", "checking")
    invoke("account", "add", "--name", "ally", "--institution", "Ally", "--type", "savings")
    invoke("categorize", "category", "add", "--name", "Groceries")
    invoke("categorize", "category", "add", "--name", "Rent")
    invoke("categorize", "category", "add", "--name", "Income", "--is-income")
    invoke("categorize", "rule", "add", "--match", "WHOLE FOODS", "--category", "Groceries")
    invoke("categorize", "rule", "add", "--match", "RENT", "--category", "Rent")
    invoke("categorize", "rule", "add", "--match", "PAYROLL", "--category", "Income")

    inbox = finance_dir / "transactions" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "chase.csv").write_text(CHASE_MIX)
    (inbox / "ally.csv").write_text(ALLY_IN)
    invoke("import", str(inbox / "chase.csv"), "--account", "chase", "--commit")
    invoke("import", str(inbox / "ally.csv"), "--account", "ally", "--commit")


# ---------- tests ----------

def test_cashflow_empty_db_returns_zeros(invoke) -> None:
    invoke("init")
    result = invoke("cashflow", "--last", "30d")
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["totals"]["inflow"] == 0.0
    assert p["totals"]["outflow"] == 0.0
    assert p["breakdown"] == []


def test_cashflow_by_category_excludes_transfers(invoke, finance_dir: Path) -> None:
    """Transfer rows get paired and are excluded from the totals by default."""
    _seed_with_data(invoke, finance_dir)
    result = invoke("cashflow", "--month", "2026-04", "--by", "category")
    p = json.loads(result.output)
    assert p["ok"] is True
    # Income $3200, + Ally interest $3.21 = 3203.21 inflow.
    # Outflow: rent 1800 + groceries 139.55 + starbucks 6.25 = 1945.80.
    # Transfer $500 excluded (paired).
    assert round(p["totals"]["inflow"], 2) == 3203.21
    assert round(p["totals"]["outflow"], 2) == 1945.80
    # Categories present: Groceries, Rent, Income, (uncategorized). NOT a transfer bucket.
    keys = {b["key"] for b in p["breakdown"]}
    assert "Groceries" in keys
    assert "Rent" in keys
    # Interest posted as +3.21 in Ally but uncategorized — so inflow reflects that too.


def test_cashflow_include_transfers_flag(invoke, finance_dir: Path) -> None:
    """--include-transfers brings the transfer rows back into totals."""
    _seed_with_data(invoke, finance_dir)
    default = json.loads(invoke("cashflow", "--month", "2026-04").output)
    with_xfer = json.loads(
        invoke("cashflow", "--month", "2026-04", "--include-transfers").output
    )
    # Including transfers increases outflow by the $500 outflow leg.
    assert with_xfer["totals"]["outflow"] > default["totals"]["outflow"]


def test_cashflow_by_merchant(invoke, finance_dir: Path) -> None:
    _seed_with_data(invoke, finance_dir)
    result = invoke("cashflow", "--month", "2026-04", "--by", "merchant")
    p = json.loads(result.output)
    merchants = [b["key"] for b in p["breakdown"]]
    # Whole Foods should be one of the heaviest merchants.
    assert any("WHOLE FOODS" in m for m in merchants)


def test_cashflow_by_account(invoke, finance_dir: Path) -> None:
    _seed_with_data(invoke, finance_dir)
    result = invoke("cashflow", "--month", "2026-04", "--by", "account")
    p = json.loads(result.output)
    keys = {b["key"] for b in p["breakdown"]}
    # Chase has most of the activity; ally has interest.
    assert "chase" in keys


def test_cashflow_bad_window_errors(invoke) -> None:
    invoke("init")
    result = invoke("cashflow", "--last", "not-a-window")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "bad_window"


def test_cashflow_bad_month_errors(invoke) -> None:
    invoke("init")
    result = invoke("cashflow", "--month", "2026-13")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "bad_window"
