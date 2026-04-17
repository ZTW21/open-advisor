"""End-to-end tests for `finance report quarterly`.

Phase 10 success criterion: running Q1 quarterly produces a proper 2-page
review. We verify the JSON payload carries every section the advisor needs
and that --write produces a structured markdown file at reports/YYYY-Qn.md.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


Q1_CSV = """Date,Description,Amount
01/02/2026,PAYROLL DEPOSIT ACME,3500.00
01/03/2026,RENT PAYMENT,-1800.00
01/05/2026,WHOLE FOODS MKT,-90.00
01/10/2026,CHIPOTLE,-14.50
01/15/2026,PAYROLL DEPOSIT ACME,3500.00
02/02/2026,PAYROLL DEPOSIT ACME,3500.00
02/03/2026,RENT PAYMENT,-1800.00
02/06/2026,WHOLE FOODS MKT,-80.00
02/15/2026,PAYROLL DEPOSIT ACME,3500.00
03/02/2026,PAYROLL DEPOSIT ACME,3500.00
03/03/2026,RENT PAYMENT,-1800.00
03/07/2026,WHOLE FOODS MKT,-95.00
03/15/2026,PAYROLL DEPOSIT ACME,3500.00
"""

Q4_2025_CSV = """Date,Description,Amount
10/02/2025,PAYROLL DEPOSIT ACME,3500.00
10/03/2025,RENT PAYMENT,-1800.00
11/02/2025,PAYROLL DEPOSIT ACME,3500.00
11/03/2025,RENT PAYMENT,-1800.00
12/02/2025,PAYROLL DEPOSIT ACME,3500.00
12/03/2025,RENT PAYMENT,-1800.00
"""


def _seed_categories_and_rules(invoke) -> None:
    invoke("categorize", "category", "add", "--name", "Salary", "--is-income")
    invoke("categorize", "category", "add", "--name", "Rent")
    invoke("categorize", "category", "add", "--name", "Groceries")
    invoke("categorize", "category", "add", "--name", "Dining")
    invoke("categorize", "rule", "add", "--match", "PAYROLL", "--category", "Salary")
    invoke("categorize", "rule", "add", "--match", "RENT", "--category", "Rent")
    invoke("categorize", "rule", "add", "--match", "WHOLE FOODS", "--category", "Groceries")
    invoke("categorize", "rule", "add", "--match", "CHIPOTLE", "--category", "Dining")


def _seed_accounts(invoke) -> None:
    invoke("account", "add", "--name", "checking",
           "--institution", "Chase", "--type", "checking", "--asset-class", "cash")
    invoke("account", "add", "--name", "brokerage",
           "--institution", "Fidelity", "--type", "brokerage",
           "--asset-class", "us_stocks",
           "--expense-ratio", "0.65", "--annual-fee", "25")
    invoke("account", "add", "--name", "retirement",
           "--institution", "Vanguard", "--type", "retirement",
           "--asset-class", "bonds",
           "--expense-ratio", "0.04")
    invoke("account", "add", "--name", "ira_intl",
           "--institution", "Vanguard", "--type", "retirement",
           "--asset-class", "intl_stocks")


def _seed_balances(invoke) -> None:
    # 2025-12-31 anchors (quarter start - 1)
    invoke("balance", "set", "--account", "checking",   "--balance", "8000",
           "--as-of", "2025-12-31")
    invoke("balance", "set", "--account", "brokerage",  "--balance", "12000",
           "--as-of", "2025-12-31")
    invoke("balance", "set", "--account", "retirement", "--balance", "22000",
           "--as-of", "2025-12-31")
    invoke("balance", "set", "--account", "ira_intl",   "--balance", "5000",
           "--as-of", "2025-12-31")
    # 2026-03-31 anchors (quarter end)
    invoke("balance", "set", "--account", "checking",   "--balance", "9500",
           "--as-of", "2026-03-31")
    invoke("balance", "set", "--account", "brokerage",  "--balance", "14000",
           "--as-of", "2026-03-31")
    invoke("balance", "set", "--account", "retirement", "--balance", "24000",
           "--as-of", "2026-03-31")
    invoke("balance", "set", "--account", "ira_intl",   "--balance", "5200",
           "--as-of", "2026-03-31")


def _seed(invoke, finance_dir: Path) -> None:
    invoke("init")
    _seed_categories_and_rules(invoke)
    _seed_accounts(invoke)

    inbox = finance_dir / "transactions" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "q1.csv").write_text(Q1_CSV)
    (inbox / "q4-2025.csv").write_text(Q4_2025_CSV)
    invoke("import", str(inbox / "q1.csv"), "--account", "checking", "--commit")
    invoke("import", str(inbox / "q4-2025.csv"), "--account", "checking", "--commit")

    _seed_balances(invoke)


def _seed_targets_and_goals(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        for ac, pct in (("cash", 30), ("us_stocks", 30),
                        ("intl_stocks", 10), ("bonds", 30)):
            conn.execute(
                "INSERT INTO allocation_targets (asset_class, target_pct, active_from) "
                "VALUES (?, ?, ?)",
                (ac, pct, "2026-01-01"),
            )
        conn.execute(
            "INSERT INTO goals (name, target_amount, target_date, priority, status) "
            "VALUES ('Emergency fund', 12000, '2026-06-30', 1, 'active')"
        )
        gid = conn.execute(
            "SELECT id FROM goals WHERE name = 'Emergency fund'"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO goals_progress (goal_id, as_of_date, amount) VALUES (?, ?, ?)",
            (gid, "2026-01-01", 8000),
        )
        conn.execute(
            "INSERT INTO goals_progress (goal_id, as_of_date, amount) VALUES (?, ?, ?)",
            (gid, "2026-03-31", 11500),
        )
        conn.commit()
    finally:
        conn.close()


# ---------- tests ----------

def test_quarterly_empty_db_returns_zeros(invoke) -> None:
    invoke("init")
    result = invoke("report", "quarterly", "--quarter", "2026-Q1")
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["quarter"] == "2026-Q1"
    assert p["start"] == "2026-01-01"
    assert p["end"] == "2026-03-31"
    assert p["totals"]["count"] == 0


def test_quarterly_bad_quarter_errors(invoke) -> None:
    invoke("init")
    result = invoke("report", "quarterly", "--quarter", "2026-Q9")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "bad_quarter"


def test_quarterly_default_is_last_complete_quarter(invoke, finance_dir: Path) -> None:
    """Today is 2026-04-17 → default quarter is 2026-Q1 (last complete)."""
    _seed(invoke, finance_dir)
    result = invoke("report", "quarterly")
    p = json.loads(result.output)
    assert p["quarter"] == "2026-Q1"


def test_quarterly_totals_and_savings_rate(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("report", "quarterly", "--quarter", "2026-Q1")
    p = json.loads(result.output)
    t = p["totals"]
    # Inflow: 6 × 3500 = 21000. Outflow: 3×1800 + 3×~88 + 14.50 = 5400 + 265 + 14.50 = 5679.50
    assert t["inflow"] == 21000.0
    assert round(t["outflow"], 2) == 5679.50
    r = p["savings_rate"]
    # Savings = inflow (income-tagged) - spend = 21000 - 5679.50
    assert r["income"] == 21000.0
    assert round(r["rate"], 4) == round((21000 - 5679.50) / 21000, 4)


def test_quarterly_net_worth_delta(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("report", "quarterly", "--quarter", "2026-Q1")
    p = json.loads(result.output)
    nw = p["net_worth"]
    # Beginning: Dec 31 2025 anchor = 8000 + 12000 + 22000 + 5000 = 47000
    assert nw["beginning"] == 47000.0
    # Ending: Mar 31 2026 = 9500 + 14000 + 24000 + 5200 = 52700
    assert nw["ending"] == 52700.0
    assert nw["delta"] == 5700.0


def test_quarterly_quarter_over_quarter(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("report", "quarterly", "--quarter", "2026-Q1")
    p = json.loads(result.output)
    qoq = p["quarter_over_quarter"]
    assert qoq["prior_quarter"] == "2025-Q4"
    # Q4 2025 outflow = 3 × 1800 = 5400
    assert round(qoq["prior_outflow"], 2) == 5400.00
    # Q1 2026 outflow = 5679.50 → delta = 279.50
    assert round(qoq["outflow_delta"], 2) == 279.50


def test_quarterly_targets_not_set_branch(invoke, finance_dir: Path) -> None:
    """Without allocation_targets rows, targets_set is False and we still
    return the payload successfully."""
    _seed(invoke, finance_dir)  # no target seeding
    result = invoke("report", "quarterly", "--quarter", "2026-Q1")
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["allocation"]["targets_set"] is False
    assert p["allocation"]["targets"] == {}
    # Drift rows still present with target_pct=None.
    for row in p["allocation"]["drift"]:
        assert row["target_pct"] is None
        assert row["drift_pp"] is None


def test_quarterly_drift_computed_vs_targets(invoke, finance_dir: Path, db_path: Path) -> None:
    _seed(invoke, finance_dir)
    _seed_targets_and_goals(db_path)
    result = invoke("report", "quarterly", "--quarter", "2026-Q1")
    p = json.loads(result.output)
    assert p["allocation"]["targets_set"] is True
    drift_by_class = {d["asset_class"]: d for d in p["allocation"]["drift"]}
    # Assets at end: checking 9500 + brokerage 14000 + retirement 24000 + ira_intl 5200 = 52700
    # us_stocks 14000/52700 ≈ 26.57%. Target 30% → drift ≈ -3.43pp.
    us = drift_by_class["us_stocks"]
    assert round(us["current_pct"], 1) == 26.6
    assert us["target_pct"] == 30
    assert round(us["drift_pp"], 1) == -3.4


def test_quarterly_fee_flagging(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("report", "quarterly", "--quarter", "2026-Q1")
    p = json.loads(result.output)
    fees = p["fees"]
    # Brokerage at 0.65% should be flagged (above default 0.25% threshold).
    flagged_names = [f["account"] for f in fees["flagged"]]
    assert "brokerage" in flagged_names
    # Retirement at 0.04% should NOT be flagged.
    assert "retirement" not in flagged_names
    # ira_intl has no fee info and is brokerage/retirement → missing_fee_info.
    assert "ira_intl" in fees["missing_fee_info"]


def test_quarterly_suggested_actions_has_drift_breach(invoke, finance_dir: Path, db_path: Path) -> None:
    _seed(invoke, finance_dir)
    # Targets that create an obvious breach (us_stocks target 60 vs. ~26.6% actual).
    conn = sqlite3.connect(str(db_path))
    try:
        for ac, pct in (("cash", 10), ("us_stocks", 60),
                        ("intl_stocks", 15), ("bonds", 15)):
            conn.execute(
                "INSERT INTO allocation_targets (asset_class, target_pct, active_from) "
                "VALUES (?, ?, ?)",
                (ac, pct, "2026-01-01"),
            )
        conn.commit()
    finally:
        conn.close()
    result = invoke("report", "quarterly", "--quarter", "2026-Q1")
    p = json.loads(result.output)
    # Should include a rebalance action that mentions us_stocks.
    joined = " | ".join(p["suggested_actions"])
    assert "us_stocks" in joined
    assert "Rebalance" in joined


def test_quarterly_write_creates_markdown(invoke, finance_dir: Path, db_path: Path) -> None:
    _seed(invoke, finance_dir)
    _seed_targets_and_goals(db_path)
    result = invoke("report", "quarterly", "--quarter", "2026-Q1", "--write")
    p = json.loads(result.output)
    assert "written_to" in p
    out = Path(p["written_to"])
    assert out.exists()
    assert out.name == "2026-Q1.md"
    body = out.read_text()
    assert "Quarterly review — 2026-Q1" in body
    assert "Rebalance check" in body
    assert "Fee audit" in body
    assert "Goals" in body
    assert "Cash flow" in body
