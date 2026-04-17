"""Tests for `finance fees` — the fee audit command."""

from __future__ import annotations

import json


def _seed(invoke) -> None:
    invoke("init")
    # Expensive brokerage: 0.65% ER + $25 flat fee → flagged.
    invoke("account", "add", "--name", "brokerage",
           "--institution", "Fidelity", "--type", "brokerage",
           "--asset-class", "us_stocks",
           "--expense-ratio", "0.65", "--annual-fee", "25")
    # Cheap retirement: 0.04% ER → not flagged.
    invoke("account", "add", "--name", "retirement",
           "--institution", "Vanguard", "--type", "retirement",
           "--asset-class", "bonds",
           "--expense-ratio", "0.04")
    # Brokerage with no fee info → missing_fee_info surfaces it.
    invoke("account", "add", "--name", "ira_intl",
           "--institution", "Vanguard", "--type", "retirement",
           "--asset-class", "intl_stocks")
    # Non-brokerage (checking) with no fees → silent, not flagged, not missing.
    invoke("account", "add", "--name", "checking",
           "--institution", "Chase", "--type", "checking",
           "--asset-class", "cash")

    invoke("balance", "set", "--account", "brokerage", "--balance", "14000",
           "--as-of", "2026-04-15")
    invoke("balance", "set", "--account", "retirement", "--balance", "24000",
           "--as-of", "2026-04-15")
    invoke("balance", "set", "--account", "ira_intl", "--balance", "5200",
           "--as-of", "2026-04-15")
    invoke("balance", "set", "--account", "checking", "--balance", "9500",
           "--as-of", "2026-04-15")


def test_fees_empty_db_returns_ok(invoke) -> None:
    invoke("init")
    result = invoke("fees")
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["accounts"] == []
    assert p["flagged"] == []
    assert p["total_annual_cost"] == 0.0
    assert p["missing_fee_info"] == []


def test_fees_flagging_above_threshold(invoke) -> None:
    _seed(invoke)
    result = invoke("fees", "--threshold", "0.25")
    p = json.loads(result.output)
    assert p["ok"] is True
    flagged_names = [f["account"] for f in p["flagged"]]
    assert "brokerage" in flagged_names
    assert "retirement" not in flagged_names


def test_fees_expense_cost_computed_from_balance(invoke) -> None:
    _seed(invoke)
    result = invoke("fees", "--as-of", "2026-04-17")
    p = json.loads(result.output)
    by_name = {a["account"]: a for a in p["accounts"]}
    # 14000 * 0.65 / 100 = 91.
    assert round(by_name["brokerage"]["expense_cost"], 2) == 91.00
    # Plus 25 flat → 116 total annual cost.
    assert round(by_name["brokerage"]["total_annual_cost"], 2) == 116.00
    # 24000 * 0.04 / 100 = 9.60.
    assert round(by_name["retirement"]["expense_cost"], 2) == 9.60
    # Total annual cost across accounts.
    assert round(p["total_annual_cost"], 2) == 125.60


def test_fees_missing_info_lists_brokerage_retirement_only(invoke) -> None:
    _seed(invoke)
    result = invoke("fees")
    p = json.loads(result.output)
    # ira_intl (retirement, no fees) → listed. checking (cash) → NOT listed.
    assert "ira_intl" in p["missing_fee_info"]
    assert "checking" not in p["missing_fee_info"]


def test_fees_custom_threshold_includes_more(invoke) -> None:
    _seed(invoke)
    result = invoke("fees", "--threshold", "0.03")
    p = json.loads(result.output)
    flagged_names = [f["account"] for f in p["flagged"]]
    assert "retirement" in flagged_names  # 0.04% > 0.03%
    assert "brokerage" in flagged_names


def test_fees_negative_threshold_errors(invoke) -> None:
    invoke("init")
    result = invoke("fees", "--threshold", "-1")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "invalid_threshold"
