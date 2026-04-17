"""End-to-end tests for `finance report annual`.

Phase 10 annual review: full-year aggregates plus the tax_pack bundle.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


YEAR_CSV = """Date,Description,Amount
01/02/2026,PAYROLL DEPOSIT ACME,3500.00
02/02/2026,PAYROLL DEPOSIT ACME,3500.00
02/14/2026,BONUS PAYMENT ACME,1000.00
03/02/2026,PAYROLL DEPOSIT ACME,3500.00
04/02/2026,PAYROLL DEPOSIT ACME,3500.00
05/02/2026,PAYROLL DEPOSIT ACME,3500.00
06/02/2026,PAYROLL DEPOSIT ACME,3500.00
07/02/2026,PAYROLL DEPOSIT ACME,3500.00
08/02/2026,PAYROLL DEPOSIT ACME,3500.00
09/02/2026,PAYROLL DEPOSIT ACME,3500.00
10/02/2026,PAYROLL DEPOSIT ACME,3500.00
11/02/2026,PAYROLL DEPOSIT ACME,3500.00
12/02/2026,PAYROLL DEPOSIT ACME,3500.00
01/05/2026,CHARITY DONATION,-500.00
02/20/2026,CHARITY DONATION,-200.00
03/10/2026,CVS PHARMACY,-75.00
05/18/2026,MORTGAGE INTEREST,-400.00
"""

PRIOR_YEAR_CSV = """Date,Description,Amount
06/15/2025,PAYROLL DEPOSIT ACME,3500.00
06/20/2025,RENT PAYMENT,-1800.00
"""


def _seed(invoke, finance_dir: Path) -> None:
    invoke("init")
    invoke("account", "add", "--name", "checking",
           "--institution", "Chase", "--type", "checking", "--asset-class", "cash")
    invoke("account", "add", "--name", "brokerage",
           "--institution", "Fidelity", "--type", "brokerage",
           "--asset-class", "us_stocks",
           "--expense-ratio", "0.65")

    invoke("categorize", "category", "add", "--name", "Salary", "--is-income")
    invoke("categorize", "category", "add", "--name", "Bonus", "--is-income")
    invoke("categorize", "category", "add", "--name", "Rent")
    invoke("categorize", "category", "add", "--name", "Charitable")
    invoke("categorize", "category", "add", "--name", "Medical")
    invoke("categorize", "category", "add", "--name", "Mortgage_Interest")
    invoke("categorize", "rule", "add", "--match", "PAYROLL",  "--category", "Salary")
    invoke("categorize", "rule", "add", "--match", "BONUS",    "--category", "Bonus")
    invoke("categorize", "rule", "add", "--match", "RENT",     "--category", "Rent")
    invoke("categorize", "rule", "add", "--match", "CHARITY",  "--category", "Charitable")
    invoke("categorize", "rule", "add", "--match", "CVS",      "--category", "Medical")
    invoke("categorize", "rule", "add", "--match", "MORTGAGE", "--category", "Mortgage_Interest")

    inbox = finance_dir / "transactions" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "year.csv").write_text(YEAR_CSV)
    (inbox / "prior.csv").write_text(PRIOR_YEAR_CSV)
    invoke("import", str(inbox / "year.csv"), "--account", "checking", "--commit")
    invoke("import", str(inbox / "prior.csv"), "--account", "checking", "--commit")

    # Anchor balances for net_worth start/end — the annual looks at Dec 31
    # of the prior year and Dec 31 of the year.
    invoke("balance", "set", "--account", "checking",  "--balance", "5000",
           "--as-of", "2025-12-31")
    invoke("balance", "set", "--account", "brokerage", "--balance", "20000",
           "--as-of", "2025-12-31")
    invoke("balance", "set", "--account", "checking",  "--balance", "10000",
           "--as-of", "2026-12-31")
    invoke("balance", "set", "--account", "brokerage", "--balance", "30000",
           "--as-of", "2026-12-31")


# ---------- tests ----------

def test_annual_empty_db_returns_zeros(invoke) -> None:
    invoke("init")
    result = invoke("report", "annual", "--year", "2026")
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["year"] == 2026
    assert p["start"] == "2026-01-01"
    assert p["end"] == "2026-12-31"
    assert p["totals"]["count"] == 0


def test_annual_bad_year_errors(invoke) -> None:
    invoke("init")
    result = invoke("report", "annual", "--year", "1800")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "bad_year"


def test_annual_default_is_last_complete_year(invoke) -> None:
    """Today is 2026-04-17 → default is 2025."""
    invoke("init")
    result = invoke("report", "annual")
    p = json.loads(result.output)
    assert p["year"] == 2025


def test_annual_totals_and_savings_rate(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("report", "annual", "--year", "2026")
    p = json.loads(result.output)
    t = p["totals"]
    # Inflow = 12×3500 + 1000 bonus = 43000
    assert t["inflow"] == 43000.0
    # Outflow = 500 + 200 + 75 + 400 = 1175
    assert round(t["outflow"], 2) == 1175.00


def test_annual_net_worth_delta(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("report", "annual", "--year", "2026")
    p = json.loads(result.output)
    nw = p["net_worth"]
    # Dec 31 2025: 5000 + 20000 = 25000
    assert nw["beginning"] == 25000.0
    # Dec 31 2026: 10000 + 30000 = 40000
    assert nw["ending"] == 40000.0
    assert nw["delta"] == 15000.0


def test_annual_year_over_year_outflow(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("report", "annual", "--year", "2026")
    p = json.loads(result.output)
    yoy = p["year_over_year"]
    assert yoy["prior_year"] == 2025
    # Prior year outflow = 1800 rent in June.
    assert round(yoy["prior_outflow"], 2) == 1800.00
    # This year outflow = 1175 → delta = -625.
    assert round(yoy["outflow_delta"], 2) == -625.00


def test_annual_tax_pack_income_and_notable(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("report", "annual", "--year", "2026")
    p = json.loads(result.output)
    pack = p["tax_pack"]
    # 12 months of salary + 1 bonus.
    assert round(pack["income"]["total"], 2) == 43000.00
    by_source = {row["category"]: row for row in pack["income"]["by_source"]}
    assert by_source["Salary"]["total"] == 42000.00
    assert by_source["Bonus"]["total"] == 1000.00
    # Notable matches: charitable, medical, mortgage_interest should all be present.
    assert "charitable" in pack["notable"]
    assert "medical" in pack["notable"]
    assert "mortgage_interest" in pack["notable"]
    # Disclaimer present.
    assert "CPA" in pack["disclaimer"] or "CPA" in pack["disclaimer"].upper() \
        or "tax" in pack["disclaimer"].lower()


def test_annual_write_creates_markdown(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("report", "annual", "--year", "2026", "--write")
    p = json.loads(result.output)
    assert "written_to" in p
    out = Path(p["written_to"])
    assert out.exists()
    assert out.name == "2026-annual.md"
    body = out.read_text()
    assert "Annual review — 2026" in body
    assert "Tax prep handoff" in body
    assert "Insurance & estate" in body
    assert "Philosophy check" in body
    assert "Allocation" in body
