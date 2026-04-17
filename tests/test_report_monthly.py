"""End-to-end tests for `finance report monthly`.

Phase 7 success criterion: the first monthly report reads like something
you'd actually act on. We verify the JSON payload has every section the
advisor needs and that --write produces a structured markdown file.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


MARCH_CSV = """Date,Description,Amount
03/01/2026,RENT PAYMENT,-1800.00
03/03/2026,WHOLE FOODS MKT #10230,-85.00
03/05/2026,PAYROLL DEPOSIT ACME,3500.00
03/07/2026,STARBUCKS #1234,-6.25
03/10/2026,WHOLE FOODS MKT #10230,-92.00
03/12/2026,AMAZON.COM,-58.99
03/14/2026,CHIPOTLE,-13.50
03/15/2026,PAYROLL DEPOSIT ACME,3500.00
03/18/2026,WHOLE FOODS MKT #10230,-71.50
03/20/2026,SHELL GAS,-45.00
03/22/2026,NETFLIX.COM,-15.99
03/25/2026,HOME DEPOT,-230.00
03/28/2026,WHOLE FOODS MKT #10230,-55.20
"""

FEB_CSV = """Date,Description,Amount
02/01/2026,RENT PAYMENT,-1800.00
02/05/2026,PAYROLL DEPOSIT ACME,3500.00
02/10/2026,WHOLE FOODS MKT #10230,-75.00
02/15/2026,PAYROLL DEPOSIT ACME,3500.00
02/20/2026,STARBUCKS #1234,-6.00
02/25/2026,WHOLE FOODS MKT #10230,-80.00
"""


def _seed(invoke, finance_dir: Path, db_path: Path) -> None:
    invoke("init")
    invoke("account", "add", "--name", "chase", "--institution", "Chase", "--type", "checking")
    invoke("categorize", "category", "add", "--name", "Rent")
    invoke("categorize", "category", "add", "--name", "Groceries")
    invoke("categorize", "category", "add", "--name", "Income", "--is-income")
    invoke("categorize", "category", "add", "--name", "Dining")
    invoke("categorize", "rule", "add", "--match", "RENT", "--category", "Rent")
    invoke("categorize", "rule", "add", "--match", "WHOLE FOODS", "--category", "Groceries")
    invoke("categorize", "rule", "add", "--match", "PAYROLL", "--category", "Income")
    invoke("categorize", "rule", "add", "--match", "CHIPOTLE", "--category", "Dining")

    inbox = finance_dir / "transactions" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "feb.csv").write_text(FEB_CSV)
    (inbox / "march.csv").write_text(MARCH_CSV)
    invoke("import", str(inbox / "feb.csv"), "--account", "chase", "--commit")
    invoke("import", str(inbox / "march.csv"), "--account", "chase", "--commit")

    # Snapshot balances so the net-worth delta has something to report.
    invoke("balance", "set", "--account", "chase", "--balance", "10000", "--as-of", "2026-02-28")
    invoke("balance", "set", "--account", "chase", "--balance", "13500", "--as-of", "2026-03-31")


def _seed_budgets_and_goals(db_path: Path) -> None:
    """Insert a budget row and a goal directly into the DB — the CLI doesn't
    yet expose these (they're Phase 2/onboarding territory)."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        gro_id = conn.execute("SELECT id FROM categories WHERE name = 'Groceries'").fetchone()["id"]
        din_id = conn.execute("SELECT id FROM categories WHERE name = 'Dining'").fetchone()["id"]
        conn.execute(
            "INSERT INTO budget_plan (category_id, amount, active_from) VALUES (?, ?, ?)",
            (gro_id, 250.00, "2026-01-01"),
        )
        conn.execute(
            "INSERT INTO budget_plan (category_id, amount, active_from) VALUES (?, ?, ?)",
            (din_id, 100.00, "2026-01-01"),
        )
        # Two goals, one on track, one red.
        conn.execute(
            "INSERT INTO goals (name, target_amount, target_date, priority, status) "
            "VALUES ('Emergency fund', 12000, '2026-06-30', 1, 'active')"
        )
        emerg_id = conn.execute(
            "SELECT id FROM goals WHERE name = 'Emergency fund'"
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO goals_progress (goal_id, as_of_date, amount) VALUES (?, ?, ?)",
            (emerg_id, "2026-01-01", 4000.00),
        )
        conn.execute(
            "INSERT INTO goals_progress (goal_id, as_of_date, amount) VALUES (?, ?, ?)",
            (emerg_id, "2026-03-31", 8000.00),
        )
        conn.execute(
            "INSERT INTO goals (name, target_amount, target_date, priority, status) "
            "VALUES ('Down payment', 60000, '2027-06-30', 2, 'active')"
        )
        dp_id = conn.execute("SELECT id FROM goals WHERE name = 'Down payment'").fetchone()["id"]
        conn.execute(
            "INSERT INTO goals_progress (goal_id, as_of_date, amount) VALUES (?, ?, ?)",
            (dp_id, "2026-01-01", 5000.00),
        )
        conn.execute(
            "INSERT INTO goals_progress (goal_id, as_of_date, amount) VALUES (?, ?, ?)",
            (dp_id, "2026-03-31", 5800.00),
        )
        conn.commit()
    finally:
        conn.close()


# ---------- tests ----------

def test_monthly_empty_db_returns_zeros(invoke) -> None:
    invoke("init")
    result = invoke("report", "monthly", "--month", "2026-03")
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["month"] == "2026-03"
    assert p["start"] == "2026-03-01"
    assert p["end"] == "2026-03-31"
    assert p["totals"]["count"] == 0


def test_monthly_totals_and_savings_rate(invoke, finance_dir: Path, db_path: Path) -> None:
    _seed(invoke, finance_dir, db_path)
    result = invoke("report", "monthly", "--month", "2026-03")
    p = json.loads(result.output)
    t = p["totals"]
    # Inflow: 3500 + 3500 = 7000.
    # Outflow: rent 1800 + groceries (85+92+71.50+55.20) = 303.70 + starbucks 6.25
    #          + amazon 58.99 + chipotle 13.50 + shell 45 + netflix 15.99 + hd 230 = 2473.43
    assert t["inflow"] == 7000.0
    assert round(t["outflow"], 2) == 2473.43
    r = p["savings_rate"]
    # Rate = (7000 - 2473.43) / 7000 = 0.6466...
    assert r["income"] == 7000.0
    assert round(r["rate"], 4) == round((7000 - 2473.43) / 7000, 4)


def test_monthly_net_worth_delta(invoke, finance_dir: Path, db_path: Path) -> None:
    _seed(invoke, finance_dir, db_path)
    result = invoke("report", "monthly", "--month", "2026-03")
    p = json.loads(result.output)
    nw = p["net_worth"]
    # Beginning = balance on/before Feb 28 = 10000.
    # Ending   = balance on/before Mar 31 = 13500.
    assert nw["beginning"] == 10000.0
    assert nw["ending"] == 13500.0
    assert nw["delta"] == 3500.0


def test_monthly_month_over_month(invoke, finance_dir: Path, db_path: Path) -> None:
    _seed(invoke, finance_dir, db_path)
    result = invoke("report", "monthly", "--month", "2026-03")
    p = json.loads(result.output)
    mom = p["month_over_month"]
    assert mom["prior_month"] == "2026-02"
    # Feb outflow = 1800 + 75 + 6 + 80 = 1961.
    assert round(mom["prior_outflow"], 2) == 1961.0
    # Mar outflow 2473.43 − 1961 = 512.43
    assert round(mom["outflow_delta"], 2) == 512.43


def test_monthly_budget_vs_actual(invoke, finance_dir: Path, db_path: Path) -> None:
    _seed(invoke, finance_dir, db_path)
    _seed_budgets_and_goals(db_path)
    result = invoke("report", "monthly", "--month", "2026-03")
    p = json.loads(result.output)
    assert len(p["budget_vs_actual"]) == 2
    # Pro-rated: 31 days / 30 = ~1.0333x the monthly budget.
    groceries = next(b for b in p["budget_vs_actual"] if b["category"] == "Groceries")
    assert round(groceries["planned"], 2) == round(250 * 31 / 30, 2)
    assert round(groceries["actual"], 2) == 303.70
    # Dining actual: Chipotle $13.50.
    dining = next(b for b in p["budget_vs_actual"] if b["category"] == "Dining")
    assert dining["actual"] == 13.50


def test_monthly_goals_status(invoke, finance_dir: Path, db_path: Path) -> None:
    _seed(invoke, finance_dir, db_path)
    _seed_budgets_and_goals(db_path)
    result = invoke("report", "monthly", "--month", "2026-03")
    p = json.loads(result.output)
    by_name = {g["name"]: g for g in p["goals"]}
    # Emergency fund: started at $4000 Jan 1, now $8000 by Mar 31, target $12000 by Jun 30.
    # Elapsed = 89d of 180d (~49%). Expected at pace = $12000 * 0.494 = $5933. Current $8000 → green.
    assert by_name["Emergency fund"]["status"] == "green"
    # Down payment: $5000 → $5800 over 89d of 545d target. Expected ≈ $9794. Current $5800 → red.
    assert by_name["Down payment"]["status"] == "red"


def test_monthly_suggested_actions_capped_at_three(invoke, finance_dir: Path, db_path: Path) -> None:
    _seed(invoke, finance_dir, db_path)
    _seed_budgets_and_goals(db_path)
    result = invoke("report", "monthly", "--month", "2026-03")
    p = json.loads(result.output)
    assert len(p["suggested_actions"]) <= 3


def test_monthly_write_creates_markdown(invoke, finance_dir: Path, db_path: Path) -> None:
    _seed(invoke, finance_dir, db_path)
    _seed_budgets_and_goals(db_path)
    result = invoke("report", "monthly", "--month", "2026-03", "--write")
    p = json.loads(result.output)
    assert "written_to" in p
    out = Path(p["written_to"])
    assert out.exists()
    assert out.name == "2026-03-monthly.md"
    body = out.read_text()
    assert "Monthly report — 2026-03" in body
    assert "Net worth" in body
    assert "Budget vs. actual" in body
    assert "Goals" in body
    assert "Suggested actions" in body


def test_monthly_bad_month_errors(invoke) -> None:
    invoke("init")
    result = invoke("report", "monthly", "--month", "2026-13")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "bad_month"


def test_monthly_default_is_prior_complete_month(invoke, finance_dir: Path, db_path: Path) -> None:
    """With no --month, the default is the month before today's month."""
    _seed(invoke, finance_dir, db_path)
    # Today is 2026-04-17 per env, so default = 2026-03.
    result = invoke("report", "monthly")
    p = json.loads(result.output)
    assert p["month"] == "2026-03"
