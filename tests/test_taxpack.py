"""Tests for `finance tax-pack` — year-end CPA handoff bundle."""

from __future__ import annotations

import json
from pathlib import Path


YEAR_CSV = """Date,Description,Amount
01/02/2026,PAYROLL DEPOSIT ACME,3500.00
01/10/2026,CHARITY DONATION,-200.00
01/20/2026,CVS PHARMACY,-50.00
02/02/2026,PAYROLL DEPOSIT ACME,3500.00
02/14/2026,BONUS PAYMENT ACME,1000.00
02/20/2026,MORTGAGE INTEREST,-400.00
03/02/2026,PAYROLL DEPOSIT ACME,3500.00
03/15/2026,WHOLE FOODS MKT,-85.00
"""


def _seed(invoke, finance_dir: Path) -> None:
    invoke("init")
    invoke("account", "add", "--name", "checking",
           "--institution", "Chase", "--type", "checking", "--asset-class", "cash")

    invoke("categorize", "category", "add", "--name", "Salary", "--is-income")
    invoke("categorize", "category", "add", "--name", "Bonus", "--is-income")
    invoke("categorize", "category", "add", "--name", "Charitable")
    invoke("categorize", "category", "add", "--name", "Medical")
    invoke("categorize", "category", "add", "--name", "Mortgage_Interest")
    invoke("categorize", "category", "add", "--name", "Groceries")
    invoke("categorize", "rule", "add", "--match", "PAYROLL",  "--category", "Salary")
    invoke("categorize", "rule", "add", "--match", "BONUS",    "--category", "Bonus")
    invoke("categorize", "rule", "add", "--match", "CHARITY",  "--category", "Charitable")
    invoke("categorize", "rule", "add", "--match", "CVS",      "--category", "Medical")
    invoke("categorize", "rule", "add", "--match", "MORTGAGE", "--category", "Mortgage_Interest")
    invoke("categorize", "rule", "add", "--match", "WHOLE FOODS", "--category", "Groceries")

    inbox = finance_dir / "transactions" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "year.csv").write_text(YEAR_CSV)
    invoke("import", str(inbox / "year.csv"), "--account", "checking", "--commit")

    invoke("balance", "set", "--account", "checking", "--balance", "8000",
           "--as-of", "2025-12-31")
    invoke("balance", "set", "--account", "checking", "--balance", "20000",
           "--as-of", "2026-12-31")


# ---------- tests ----------

def test_taxpack_empty_db_ok(invoke) -> None:
    invoke("init")
    result = invoke("tax-pack", "--year", "2026")
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["year"] == 2026
    assert p["income"]["total"] == 0.0
    assert p["spend_by_category"] == []


def test_taxpack_default_is_last_complete_year(invoke) -> None:
    """Today is 2026-04-17 → default year is 2025."""
    invoke("init")
    result = invoke("tax-pack")
    p = json.loads(result.output)
    assert p["year"] == 2025


def test_taxpack_bad_year_errors(invoke) -> None:
    invoke("init")
    result = invoke("tax-pack", "--year", "1800")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "bad_year"


def test_taxpack_income_aggregation(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("tax-pack", "--year", "2026")
    p = json.loads(result.output)
    # Salary: 3×3500 = 10500. Bonus: 1000. Total: 11500.
    assert p["income"]["total"] == 11500.0
    by_source = {row["category"]: row for row in p["income"]["by_source"]}
    assert by_source["Salary"]["total"] == 10500.0
    assert by_source["Salary"]["count"] == 3
    assert by_source["Bonus"]["total"] == 1000.0


def test_taxpack_spend_by_category(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("tax-pack", "--year", "2026")
    p = json.loads(result.output)
    spend = {row["category"]: row for row in p["spend_by_category"]}
    assert spend["Mortgage_Interest"]["total"] == 400.0
    assert spend["Charitable"]["total"] == 200.0
    assert spend["Medical"]["total"] == 50.0
    assert spend["Groceries"]["total"] == 85.0


def test_taxpack_net_worth_anchors(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("tax-pack", "--year", "2026")
    p = json.loads(result.output)
    nw = p["net_worth"]
    assert nw["beginning"] == 8000.0  # Dec 31 2025
    assert nw["ending"] == 20000.0    # Dec 31 2026
    assert nw["delta"] == 12000.0


def test_taxpack_notable_matching(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("tax-pack", "--year", "2026")
    p = json.loads(result.output)
    notable = p["notable"]
    # Category names contain the keyword substrings we match against.
    assert "charitable" in notable
    assert "medical" in notable
    assert "mortgage_interest" in notable
    # Each match surfaces the full category row (total + count).
    charity_rows = notable["charitable"]
    assert any(r["category"] == "Charitable" and r["total"] == 200.0
               for r in charity_rows)


def test_taxpack_disclaimer_present(invoke) -> None:
    invoke("init")
    result = invoke("tax-pack", "--year", "2026")
    p = json.loads(result.output)
    assert "disclaimer" in p
    assert "CPA" in p["disclaimer"] or "tax" in p["disclaimer"].lower()
