"""Tests for `finance afford`."""

from __future__ import annotations

import json
import sqlite3


def _setup(invoke, db_path) -> None:
    """Set up a finance dir with a checking account, savings, and 3 months of txns."""
    invoke("init")
    invoke(
        "account", "add",
        "--name", "chase_checking",
        "--institution", "Chase",
        "--type", "checking",
    )
    invoke(
        "account", "add",
        "--name", "ally_savings",
        "--institution", "Ally",
        "--type", "savings",
    )
    invoke("balance", "set", "--account", "chase_checking", "--balance", "3500", "--as-of", "2026-04-15")
    invoke("balance", "set", "--account", "ally_savings", "--balance", "8000", "--as-of", "2026-04-15")

    # Seed transactions: 3 months of $6k payroll + $1800 rent + $600 groceries.
    conn = sqlite3.connect(str(db_path))
    try:
        for name, is_inc in [("Payroll", 1), ("Rent", 0), ("Groceries", 0)]:
            conn.execute(
                "INSERT INTO categories (name, is_income, is_transfer) VALUES (?, ?, 0)",
                (name, is_inc),
            )
        conn.commit()
        pid = conn.execute("SELECT id FROM categories WHERE name='Payroll'").fetchone()[0]
        rid = conn.execute("SELECT id FROM categories WHERE name='Rent'").fetchone()[0]
        gid = conn.execute("SELECT id FROM categories WHERE name='Groceries'").fetchone()[0]
        aid = conn.execute("SELECT id FROM accounts WHERE name='chase_checking'").fetchone()[0]
        for month in [1, 2, 3]:
            for key, d, amt, desc, cat in [
                (f"pay-{month}", f"2026-{month:02d}-02", 6000.0, f"Payroll m{month}", pid),
                (f"rent-{month}", f"2026-{month:02d}-05", -1800.0, f"Rent m{month}", rid),
                (f"gro-{month}", f"2026-{month:02d}-12", -600.0, f"Groc m{month}", gid),
            ]:
                conn.execute(
                    "INSERT INTO transactions (account_id, date, amount, description_raw, "
                    "category_id, dedup_key) VALUES (?, ?, ?, ?, ?, ?)",
                    (aid, d, amt, desc, cat, key),
                )
        conn.commit()
    finally:
        conn.close()


def test_afford_green_small_purchase(invoke, db_path) -> None:
    """A purchase that fits within one month's free cash returns green."""
    _setup(invoke, db_path)
    result = invoke("afford", "500", "--as-of", "2026-04-17")
    assert result.exit_code == 0, result.output
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["verdict"] == "green"
    assert p["verdict_reason"] == "fits_in_monthly_free_cash"
    assert p["cushion"]["liquid_cash_before"] == 11500.0
    assert p["cushion"]["liquid_cash_after"] == 11000.0
    assert p["cushion"]["monthly_outflow"] == 2400.0  # (1800+600) per mo
    assert p["cushion"]["months_of_cushion_before"] == round(11500 / 2400, 1)


def test_afford_yellow_dips_into_savings(invoke, db_path) -> None:
    """Purchase above monthly free cash but cushion intact → yellow."""
    _setup(invoke, db_path)
    # $3000 > 2400 free cash, but leaves ~$8.5k cushion (> 1 month of 2400).
    result = invoke("afford", "3000", "--min-months", "1", "--as-of", "2026-04-17")
    p = json.loads(result.output)
    assert p["verdict"] == "yellow"
    assert p["verdict_reason"] == "dips_into_savings_but_keeps_cushion"


def test_afford_red_breaches_cushion(invoke, db_path) -> None:
    """Purchase that drops cushion below min-months → red."""
    _setup(invoke, db_path)
    result = invoke("afford", "10000", "--min-months", "3", "--as-of", "2026-04-17")
    p = json.loads(result.output)
    assert p["verdict"] == "red"
    assert p["verdict_reason"] == "breaches_cushion"
    # Cushion after = 1500, outflow 2400 → ~0.6mo, < 3.
    assert p["cushion"]["months_of_cushion_after"] < 3


def test_afford_invalid_amount(invoke) -> None:
    invoke("init")
    result = invoke("afford", "0")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "invalid_amount"


def test_afford_no_outflow_history_is_red(invoke) -> None:
    """With no transactions, we can't compute a cushion — default to red."""
    invoke("init")
    invoke(
        "account", "add", "--name", "checking",
        "--institution", "Chase", "--type", "checking",
    )
    invoke("balance", "set", "--account", "checking", "--balance", "5000", "--as-of", "2026-04-15")
    result = invoke("afford", "500", "--as-of", "2026-04-17")
    p = json.loads(result.output)
    assert p["verdict"] == "red"
    assert p["verdict_reason"] == "no_outflow_history"
