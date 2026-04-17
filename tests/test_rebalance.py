"""Tests for `finance rebalance`."""

from __future__ import annotations

import json
import sqlite3


def _seed_targets(db_path, targets: dict, active_from: str = "2026-01-01") -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        for ac, pct in targets.items():
            conn.execute(
                "INSERT INTO allocation_targets (asset_class, target_pct, active_from) "
                "VALUES (?, ?, ?)",
                (ac, pct, active_from),
            )
        conn.commit()
    finally:
        conn.close()


def _seed_portfolio(invoke) -> None:
    invoke("init")
    invoke("account", "add", "--name", "checking", "--institution", "Chase",
           "--type", "checking", "--asset-class", "cash")
    invoke("account", "add", "--name", "savings", "--institution", "Ally",
           "--type", "savings", "--asset-class", "cash")
    invoke("account", "add", "--name", "brokerage", "--institution", "Fidelity",
           "--type", "brokerage", "--asset-class", "us_stocks")
    invoke("account", "add", "--name", "retirement", "--institution", "Vanguard",
           "--type", "retirement", "--asset-class", "bonds")
    invoke("balance", "set", "--account", "checking", "--balance", "3500", "--as-of", "2026-04-15")
    invoke("balance", "set", "--account", "savings", "--balance", "8000", "--as-of", "2026-04-15")
    invoke("balance", "set", "--account", "brokerage", "--balance", "15000", "--as-of", "2026-04-15")
    invoke("balance", "set", "--account", "retirement", "--balance", "25000", "--as-of", "2026-04-15")


def test_rebalance_no_targets(invoke) -> None:
    """Without targets, report current allocation and flag targets_set=false."""
    _seed_portfolio(invoke)
    result = invoke("rebalance", "--as-of", "2026-04-17")
    assert result.exit_code == 0, result.output
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["targets_set"] is False
    # 3500 + 8000 + 15000 + 25000 = 51500
    assert p["assets_total"] == 51500.0
    classes = {c["asset_class"]: c for c in p["current_allocation"]}
    assert classes["cash"]["balance"] == 11500.0
    assert classes["us_stocks"]["balance"] == 15000.0
    assert classes["bonds"]["balance"] == 25000.0


def test_rebalance_within_tolerance(invoke, db_path) -> None:
    """Targets matching current allocation within tolerance → on_target."""
    _seed_portfolio(invoke)
    _seed_targets(db_path, {"cash": 22.3, "us_stocks": 29.1, "bonds": 48.6})
    result = invoke("rebalance", "--tolerance", "5", "--as-of", "2026-04-17")
    p = json.loads(result.output)
    assert p["targets_set"] is True
    statuses = {row["asset_class"]: row["status"] for row in p["drift"]}
    assert statuses["cash"] == "on_target"
    assert statuses["us_stocks"] == "on_target"
    assert statuses["bonds"] == "on_target"
    # No suggestions when every class is on target.
    assert p["suggestions"] == []


def test_rebalance_flags_breach(invoke, db_path) -> None:
    """When current drifts >2x tolerance from target → breach."""
    _seed_portfolio(invoke)
    _seed_targets(db_path, {"cash": 10, "us_stocks": 50, "intl_stocks": 20, "bonds": 20})
    result = invoke("rebalance", "--tolerance", "5", "--as-of", "2026-04-17")
    p = json.loads(result.output)
    statuses = {row["asset_class"]: row["status"] for row in p["drift"]}
    # Current: cash 22.3%, us_stocks 29.1%, bonds 48.5%, intl_stocks 0%
    # Targets: 10, 50, 20, 20.
    assert statuses["cash"] == "breach"          # +12.3pp
    assert statuses["us_stocks"] == "breach"     # -20.9pp
    assert statuses["bonds"] == "breach"         # +28.5pp
    assert statuses["intl_stocks"] == "breach"   # -20pp
    # Suggestions exist and are sorted by magnitude.
    assert len(p["suggestions"]) == 4
    mags = [abs(s["drift_pp"]) for s in p["suggestions"]]
    assert mags == sorted(mags, reverse=True)


def test_rebalance_warning_on_bad_target_sum(invoke, db_path) -> None:
    """Targets that don't sum to 100 produce a warning."""
    _seed_portfolio(invoke)
    _seed_targets(db_path, {"cash": 10, "us_stocks": 30, "bonds": 20})  # sum=60
    result = invoke("rebalance", "--as-of", "2026-04-17")
    p = json.loads(result.output)
    assert any("not 100%" in w for w in p["warnings"])


def test_rebalance_liabilities_excluded(invoke, db_path) -> None:
    """Credit cards are excluded from the allocation total."""
    _seed_portfolio(invoke)
    invoke("account", "add", "--name", "chase_card", "--institution", "Chase",
           "--type", "credit_card", "--apr", "24.99", "--min-payment", "50")
    invoke("balance", "set", "--account", "chase_card", "--balance", "4000", "--as-of", "2026-04-15")
    result = invoke("rebalance", "--as-of", "2026-04-17")
    p = json.loads(result.output)
    # Liability should not show up in current_allocation or affect the total.
    classes = [c["asset_class"] for c in p["current_allocation"]]
    assert "liability" not in classes
    assert p["assets_total"] == 51500.0  # unchanged


def test_rebalance_invalid_tolerance(invoke) -> None:
    invoke("init")
    result = invoke("rebalance", "--tolerance", "-1")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "invalid_tolerance"
