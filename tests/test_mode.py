"""Tests for `finance mode` — behavioral mode classifier (Phase 11).

The mode shapes the advisor's tone and priorities. We test the three
branches (debt / invest / balanced) plus the "missing input" edge cases.
"""

from __future__ import annotations

import json
from pathlib import Path


# ---------- seed helpers ----------

def _init(invoke) -> None:
    invoke("init")


def _add_categories(invoke) -> None:
    invoke("categorize", "category", "add", "--name", "Salary", "--is-income")
    invoke("categorize", "category", "add", "--name", "Groceries")
    invoke("categorize", "category", "add", "--name", "Rent")
    invoke("categorize", "rule", "add", "--match", "PAYROLL",  "--category", "Salary")
    invoke("categorize", "rule", "add", "--match", "GROCERY",  "--category", "Groceries")
    invoke("categorize", "rule", "add", "--match", "RENT",     "--category", "Rent")


def _seed_outflow(invoke, finance_dir: Path, monthly: float = 3000.0) -> None:
    """Seed three months of outflow so trailing_monthly_outflow isn't zero."""
    rows = ["Date,Description,Amount"]
    for m in (1, 2, 3):
        rows.append(f"{m:02d}/05/2026,RENT PAYMENT,-{monthly * 0.5:.2f}")
        rows.append(f"{m:02d}/15/2026,GROCERY STORE,-{monthly * 0.5:.2f}")
    inbox = finance_dir / "transactions" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "outflow.csv").write_text("\n".join(rows) + "\n")
    invoke("import", str(inbox / "outflow.csv"),
           "--account", "checking", "--commit")


# ---------- tests ----------

def test_mode_empty_db_is_balanced(invoke) -> None:
    _init(invoke)
    result = invoke("mode")
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["mode"] == "balanced"
    assert p["inputs"]["high_apr_debt_total"] == 0
    assert p["inputs"]["allocation_targets_set"] is False
    assert p["inputs"]["emergency_fund_months"] is None


def test_mode_high_apr_debt_flips_to_debt(invoke) -> None:
    _init(invoke)
    invoke("account", "add",
           "--name", "chase",
           "--institution", "Chase",
           "--type", "credit_card",
           "--apr", "24.99",
           "--min-payment", "50")
    invoke("balance", "set", "--account", "chase", "--balance", "4200",
           "--as-of", "2026-04-01")
    result = invoke("mode")
    p = json.loads(result.output)
    assert p["mode"] == "debt"
    assert p["inputs"]["high_apr_debt_total"] == 4200.0
    assert len(p["inputs"]["high_apr_accounts"]) == 1
    assert p["inputs"]["high_apr_accounts"][0]["name"] == "chase"
    # The reason string should mention the debt.
    assert any("chase" in r.lower() for r in p["reasons"])


def test_mode_low_apr_loan_does_not_trigger_debt_mode(invoke) -> None:
    """A 6% student loan or 3% mortgage should not flip to debt mode."""
    _init(invoke)
    invoke("account", "add",
           "--name", "student",
           "--institution", "Nelnet",
           "--type", "loan",
           "--apr", "5.5",
           "--min-payment", "200")
    invoke("balance", "set", "--account", "student", "--balance", "15000",
           "--as-of", "2026-04-01")
    result = invoke("mode")
    p = json.loads(result.output)
    # Below the 8% threshold → not 'debt'.
    assert p["mode"] != "debt"
    assert p["inputs"]["high_apr_debt_total"] == 0.0


def test_mode_mortgage_excluded_even_above_threshold(invoke) -> None:
    """A 9% mortgage (e.g., historical) is excluded regardless of APR."""
    _init(invoke)
    invoke("account", "add",
           "--name", "house",
           "--institution", "Bank",
           "--type", "mortgage",
           "--apr", "9.0",
           "--min-payment", "2000")
    invoke("balance", "set", "--account", "house", "--balance", "300000",
           "--as-of", "2026-04-01")
    result = invoke("mode")
    p = json.loads(result.output)
    assert p["mode"] != "debt"
    assert p["inputs"]["high_apr_debt_total"] == 0.0


def test_mode_invest_requires_all_three_conditions(invoke, finance_dir: Path) -> None:
    """Invest mode needs: no high-APR debt + EF >= 3mo + targets set."""
    _init(invoke)
    invoke("account", "add", "--name", "checking",
           "--institution", "Chase", "--type", "checking",
           "--asset-class", "cash")
    invoke("balance", "set", "--account", "checking",
           "--balance", "20000", "--as-of", "2026-03-31")
    _add_categories(invoke)
    _seed_outflow(invoke, finance_dir, monthly=3000.0)

    # Before targets: balanced (no targets set).
    result = invoke("mode")
    p = json.loads(result.output)
    assert p["mode"] == "balanced"
    assert any("targets" in r.lower() for r in p["reasons"])

    # Now set allocation targets directly.
    import sqlite3
    db_path = finance_dir / "data" / "finance.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO allocation_targets (asset_class, target_pct, active_from) "
        "VALUES ('cash', 100, '2026-01-01')"
    )
    conn.commit()
    conn.close()

    result = invoke("mode")
    p = json.loads(result.output)
    assert p["mode"] == "invest"
    assert p["inputs"]["allocation_targets_set"] is True
    assert p["inputs"]["emergency_fund_months"] is not None
    assert p["inputs"]["emergency_fund_months"] >= 3.0


def test_mode_balanced_when_emergency_fund_short(invoke, finance_dir: Path) -> None:
    """No high-APR debt + targets set + EF < 3mo → still balanced, not invest."""
    _init(invoke)
    invoke("account", "add", "--name", "checking",
           "--institution", "Chase", "--type", "checking",
           "--asset-class", "cash")
    # Only 1 month of coverage.
    invoke("balance", "set", "--account", "checking",
           "--balance", "3000", "--as-of", "2026-03-31")
    _add_categories(invoke)
    _seed_outflow(invoke, finance_dir, monthly=3000.0)

    import sqlite3
    db_path = finance_dir / "data" / "finance.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO allocation_targets (asset_class, target_pct, active_from) "
        "VALUES ('cash', 100, '2026-01-01')"
    )
    conn.commit()
    conn.close()

    result = invoke("mode")
    p = json.loads(result.output)
    assert p["mode"] == "balanced"
    ef = p["inputs"]["emergency_fund_months"]
    assert ef is not None and ef < 3.0


def test_mode_bad_as_of_errors(invoke) -> None:
    _init(invoke)
    result = invoke("mode", "--as-of", "not-a-date")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "bad_date"


def test_mode_reasons_always_populated(invoke) -> None:
    """The `reasons` list is how the advisor explains its classification."""
    _init(invoke)
    result = invoke("mode")
    p = json.loads(result.output)
    assert isinstance(p["reasons"], list)
    assert len(p["reasons"]) >= 1
