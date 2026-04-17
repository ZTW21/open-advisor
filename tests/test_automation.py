"""Tests for `finance automation` — recurring-outflow detection (Phase 11)."""

from __future__ import annotations

import json
from pathlib import Path


SUBSCRIPTION_CSV = """Date,Description,Amount
01/03/2026,NETFLIX,-15.99
01/05/2026,ADOBE CREATIVE,-20.99
01/10/2026,GROCERY STORE,-142.37
02/03/2026,NETFLIX,-15.99
02/05/2026,ADOBE CREATIVE,-20.99
02/18/2026,GROCERY STORE,-98.42
03/03/2026,NETFLIX,-15.99
03/05/2026,ADOBE CREATIVE,-20.99
03/22/2026,GROCERY STORE,-120.50
03/12/2026,ONE-TIME PURCHASE,-250.00
"""


def _seed(invoke, finance_dir: Path) -> None:
    invoke("init")
    invoke("account", "add", "--name", "checking",
           "--institution", "Chase", "--type", "checking",
           "--asset-class", "cash")
    invoke("categorize", "category", "add", "--name", "Streaming")
    invoke("categorize", "category", "add", "--name", "Software")
    invoke("categorize", "category", "add", "--name", "Groceries")
    invoke("categorize", "rule", "add", "--match", "NETFLIX",  "--category", "Streaming")
    invoke("categorize", "rule", "add", "--match", "ADOBE",    "--category", "Software")
    invoke("categorize", "rule", "add", "--match", "GROCERY",  "--category", "Groceries")
    inbox = finance_dir / "transactions" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "subs.csv").write_text(SUBSCRIPTION_CSV)
    invoke("import", str(inbox / "subs.csv"),
           "--account", "checking", "--commit")


# ---------- tests ----------

def test_automation_empty_db_ok(invoke) -> None:
    invoke("init")
    # `as-of` is in April; a fresh DB has no transactions.
    result = invoke("automation", "--as-of", "2026-04-15")
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["recurring"] == []
    assert p["total_estimated_annual"] == 0


def test_automation_detects_monthly_subscriptions(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    # As-of Apr 15 2026 → full months Jan-Mar are in the lookback window.
    result = invoke("automation",
                    "--as-of", "2026-04-15",
                    "--lookback-months", "6")
    p = json.loads(result.output)
    merchants = {r["merchant"]: r for r in p["recurring"]}
    # NETFLIX and ADOBE CREATIVE both appear in 3 distinct months with
    # stable amounts → should be flagged.
    assert any("NETFLIX" in m for m in merchants)
    assert any("ADOBE" in m for m in merchants)


def test_automation_excludes_non_recurring(invoke, finance_dir: Path) -> None:
    """A one-time large charge should NOT appear in recurring."""
    _seed(invoke, finance_dir)
    result = invoke("automation",
                    "--as-of", "2026-04-15",
                    "--lookback-months", "6")
    p = json.loads(result.output)
    for row in p["recurring"]:
        assert "ONE-TIME" not in row["merchant"].upper()


def test_automation_grocery_passes_with_loose_tolerance(
    invoke, finance_dir: Path
) -> None:
    """Groceries vary a lot per month; with loose tolerance they still pass."""
    _seed(invoke, finance_dir)
    strict = invoke("automation",
                    "--as-of", "2026-04-15",
                    "--lookback-months", "6",
                    "--tolerance", "0.05")  # ±5% — groceries will fail this
    p_strict = json.loads(strict.output)
    grocery_strict = any(
        "GROCERY" in r["merchant"] for r in p_strict["recurring"]
    )

    loose = invoke("automation",
                   "--as-of", "2026-04-15",
                   "--lookback-months", "6",
                   "--tolerance", "0.5")  # ±50%
    p_loose = json.loads(loose.output)
    grocery_loose = any(
        "GROCERY" in r["merchant"] for r in p_loose["recurring"]
    )

    # Strict should drop groceries (amounts 142 and 98 differ by ~36%);
    # loose should include them.
    assert not grocery_strict
    assert grocery_loose


def test_automation_annual_cost_is_monthly_times_twelve(
    invoke, finance_dir: Path
) -> None:
    _seed(invoke, finance_dir)
    result = invoke("automation", "--as-of", "2026-04-15")
    p = json.loads(result.output)
    for row in p["recurring"]:
        assert row["estimated_annual"] == round(row["estimated_monthly"] * 12, 2)


def test_automation_bad_lookback_errors(invoke) -> None:
    invoke("init")
    result = invoke("automation", "--lookback-months", "0")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "bad_lookback"


def test_automation_bad_min_hits_errors(invoke) -> None:
    invoke("init")
    result = invoke("automation", "--min-hits", "0")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "bad_min_hits"


def test_automation_bad_tolerance_errors(invoke) -> None:
    invoke("init")
    result = invoke("automation", "--tolerance", "-0.1")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "bad_tolerance"


def test_automation_bad_as_of_errors(invoke) -> None:
    invoke("init")
    result = invoke("automation", "--as-of", "not-a-date")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "bad_date"
