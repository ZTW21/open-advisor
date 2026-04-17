"""End-to-end tests for `finance report daily` and `finance report weekly`.

These verify the Phase 6 success criterion: the advisor produces a useful
one-sentence daily and a ~150-word weekly automatically. We test the CLI
payload (what the advisor reads) and the written markdown file.
"""

from __future__ import annotations

import json
from pathlib import Path


WEEK_CSV = """Date,Description,Amount
04/06/2026,RENT PAYMENT,-1800.00
04/07/2026,WHOLE FOODS MKT #10230,-52.10
04/08/2026,STARBUCKS #1234,-6.25
04/09/2026,WHOLE FOODS MKT #10230,-45.32
04/10/2026,PAYROLL DEPOSIT ACME,3200.00
04/10/2026,STARBUCKS #1234,-7.15
04/11/2026,NETFLIX.COM,-15.99
04/12/2026,WHOLE FOODS MKT #10230,-38.00
"""


def _seed(invoke, finance_dir: Path) -> None:
    invoke("init")
    invoke("account", "add", "--name", "chase", "--institution", "Chase", "--type", "checking")
    invoke("categorize", "category", "add", "--name", "Groceries")
    invoke("categorize", "category", "add", "--name", "Rent")
    invoke("categorize", "category", "add", "--name", "Income", "--is-income")
    invoke("categorize", "rule", "add", "--match", "WHOLE FOODS", "--category", "Groceries")
    invoke("categorize", "rule", "add", "--match", "RENT", "--category", "Rent")
    invoke("categorize", "rule", "add", "--match", "PAYROLL", "--category", "Income")

    inbox = finance_dir / "transactions" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "week.csv").write_text(WEEK_CSV)
    invoke("import", str(inbox / "week.csv"), "--account", "chase", "--commit")


# ---------- daily ----------

def test_daily_payload_empty_db(invoke) -> None:
    invoke("init")
    result = invoke("report", "daily", "--date", "2026-04-10")
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["totals"]["count"] == 0
    assert "No activity" in p["suggested_sentence"]


def test_daily_payload_with_activity(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("report", "daily", "--date", "2026-04-10")
    p = json.loads(result.output)
    # On 2026-04-10 we have payroll $3200 and Starbucks -$7.15.
    # Transfers excluded: none here.
    assert p["totals"]["inflow"] == 3200.0
    assert round(p["totals"]["outflow"], 2) == 7.15
    assert p["totals"]["count"] == 2
    assert "2026-04-10" in p["suggested_sentence"]


def test_daily_write_creates_markdown(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("report", "daily", "--date", "2026-04-10", "--write")
    p = json.loads(result.output)
    assert "written_to" in p
    written = Path(p["written_to"])
    assert written.exists()
    assert written.name == "2026-04-10-daily.md"
    body = written.read_text()
    assert "Daily brief — 2026-04-10" in body


def test_daily_bad_date_errors(invoke) -> None:
    invoke("init")
    result = invoke("report", "daily", "--date", "not-a-date")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "bad_date"


# ---------- weekly ----------

def test_weekly_payload_for_specific_week(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    # 2026-04-06 is a Monday; its ISO week is W15.
    result = invoke("report", "weekly", "--week", "2026-w15")
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["week"] == "2026-w15"
    assert p["start"] == "2026-04-06"
    assert p["end"] == "2026-04-12"
    # Week contains: rent -1800, 3 grocery runs totaling 135.42, 2 starbucks 13.40,
    # payroll +3200, netflix -15.99  → outflow = 1964.81, inflow = 3200.
    assert p["totals"]["inflow"] == 3200.0
    assert round(p["totals"]["outflow"], 2) == 1964.81
    # by_category has Rent and Groceries
    cat_keys = {b["key"] for b in p["by_category"]}
    assert "Rent" in cat_keys
    assert "Groceries" in cat_keys


def test_weekly_write_creates_markdown(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("report", "weekly", "--week", "2026-w15", "--write")
    p = json.loads(result.output)
    assert "written_to" in p
    written = Path(p["written_to"])
    assert written.exists()
    assert written.name == "2026-w15-weekly.md"
    body = written.read_text()
    assert "Weekly summary — 2026-w15" in body
    assert "Top categories" in body


def test_weekly_bad_week_errors(invoke) -> None:
    invoke("init")
    result = invoke("report", "weekly", "--week", "nonsense")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "bad_week"


def test_weekly_pace_comparison_zero_when_no_history(invoke, finance_dir: Path) -> None:
    """With no prior weeks, the pace delta is 0 and pct is None."""
    _seed(invoke, finance_dir)
    result = invoke("report", "weekly", "--week", "2026-w15")
    p = json.loads(result.output)
    assert p["pace"]["prior_4wk_median_outflow"] == 0.0
    assert p["pace"]["delta_pct"] is None
