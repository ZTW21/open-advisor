"""Tests for `finance payoff` and the simulate_payoff analytic."""

from __future__ import annotations

import json

from finance_advisor.analytics import Debt, simulate_payoff


# ---------- unit tests: simulate_payoff ----------

def _two_cards() -> list[Debt]:
    """Two credit cards: higher APR has higher balance."""
    return [
        Debt(
            account_id=1, name="chase", account_type="credit_card",
            balance=4200.0, apr=24.99, min_payment=50.0, as_of_date="2026-04-15",
        ),
        Debt(
            account_id=2, name="discover", account_type="credit_card",
            balance=1800.0, apr=18.0, min_payment=35.0, as_of_date="2026-04-15",
        ),
    ]


def test_avalanche_converges_with_enough_extra() -> None:
    debts = _two_cards()
    result = simulate_payoff(debts, strategy="avalanche", extra_monthly=200.0)
    assert result["converged"] is True
    assert result["months"] > 0
    # Chase (higher APR) should clear first under avalanche.
    by_name = {d["name"]: d for d in result["by_debt"]}
    assert by_name["chase"]["months_to_zero"] is not None
    assert by_name["discover"]["months_to_zero"] is not None
    assert by_name["chase"]["months_to_zero"] < by_name["discover"]["months_to_zero"]


def test_snowball_pays_smallest_first() -> None:
    debts = _two_cards()
    result = simulate_payoff(debts, strategy="snowball", extra_monthly=200.0)
    assert result["converged"] is True
    by_name = {d["name"]: d for d in result["by_debt"]}
    # Discover (smaller balance) should clear first under snowball.
    assert by_name["discover"]["months_to_zero"] < by_name["chase"]["months_to_zero"]


def test_avalanche_total_interest_beats_snowball() -> None:
    """Avalanche minimizes interest by definition. Snowball charges more."""
    debts = _two_cards()
    av = simulate_payoff(debts, strategy="avalanche", extra_monthly=200.0)
    sn = simulate_payoff(debts, strategy="snowball", extra_monthly=200.0)
    assert av["total_interest"] < sn["total_interest"]


def test_does_not_converge_when_extra_too_small() -> None:
    """Chase min=$50 at 24.99% APR on $4,200 accrues ~$87/mo interest —
    without extra, simulation won't converge."""
    debts = _two_cards()
    result = simulate_payoff(debts, strategy="avalanche", extra_monthly=0.0)
    assert result["converged"] is False
    assert any("did not converge" in w for w in result["warnings"])


def test_missing_apr_treated_as_zero_with_warning() -> None:
    debts = [
        Debt(
            account_id=1, name="x", account_type="loan",
            balance=1000.0, apr=None, min_payment=100.0, as_of_date="2026-04-15",
        ),
    ]
    result = simulate_payoff(debts, strategy="avalanche", extra_monthly=0.0)
    assert result["converged"] is True
    # 0% APR, $100/mo on $1000 → 10 months.
    assert result["months"] == 10
    assert any("no APR set" in w for w in result["warnings"])


def test_custom_order_requires_order_arg() -> None:
    debts = _two_cards()
    try:
        simulate_payoff(debts, strategy="custom", extra_monthly=50.0)
    except ValueError as e:
        assert "custom_order" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_custom_order_honored() -> None:
    """User-specified order overrides APR/balance-based defaults."""
    debts = _two_cards()
    # Explicitly prioritize discover despite chase being higher APR.
    result = simulate_payoff(
        debts,
        strategy="custom",
        extra_monthly=200.0,
        custom_order=["discover", "chase"],
    )
    assert result["converged"] is True
    by_name = {d["name"]: d for d in result["by_debt"]}
    assert by_name["discover"]["months_to_zero"] < by_name["chase"]["months_to_zero"]


# ---------- CLI tests: finance payoff ----------

def _seed_debts(invoke) -> None:
    invoke("init")
    invoke(
        "account", "add",
        "--name", "chase",
        "--institution", "Chase",
        "--type", "credit_card",
        "--apr", "24.99",
        "--min-payment", "50",
    )
    invoke(
        "account", "add",
        "--name", "discover",
        "--institution", "Discover",
        "--type", "credit_card",
        "--apr", "18.0",
        "--min-payment", "35",
    )
    invoke("balance", "set", "--account", "chase", "--balance", "4200", "--as-of", "2026-04-15")
    invoke("balance", "set", "--account", "discover", "--balance", "1800", "--as-of", "2026-04-15")


def test_payoff_no_debts(invoke) -> None:
    invoke("init")
    result = invoke("payoff", "--as-of", "2026-04-17")
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["no_debts"] is True


def test_payoff_avalanche_cli(invoke) -> None:
    _seed_debts(invoke)
    result = invoke("payoff", "--strategy", "avalanche", "--extra", "200", "--as-of", "2026-04-17")
    assert result.exit_code == 0, result.output
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["strategy"] == "avalanche"
    assert p["total_balance"] == 6000.0
    assert p["result"]["converged"] is True


def test_payoff_compare(invoke) -> None:
    _seed_debts(invoke)
    result = invoke(
        "payoff", "--strategy", "avalanche", "--extra", "200",
        "--compare", "--as-of", "2026-04-17",
    )
    p = json.loads(result.output)
    assert p["comparison"] is not None
    assert p["comparison"]["strategy"] == "snowball"
    # Avalanche should be at least as efficient.
    assert p["result"]["total_interest"] <= p["comparison"]["total_interest"]


def test_payoff_custom_requires_order(invoke) -> None:
    _seed_debts(invoke)
    result = invoke("payoff", "--strategy", "custom", "--as-of", "2026-04-17")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "missing_order"


def test_payoff_custom_unknown_account(invoke) -> None:
    _seed_debts(invoke)
    result = invoke(
        "payoff", "--strategy", "custom", "--order", "ghost,chase",
        "--as-of", "2026-04-17",
    )
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "unknown_accounts"


def test_payoff_invalid_extra(invoke) -> None:
    _seed_debts(invoke)
    result = invoke("payoff", "--extra", "-10", "--as-of", "2026-04-17")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "invalid_extra"
