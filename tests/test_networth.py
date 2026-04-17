"""Tests for `finance net-worth`.

Phase 1 success criterion: `finance init && finance net-worth --json`
returns a valid (empty) result.
"""

from __future__ import annotations

import json


def test_networth_empty_db(invoke) -> None:
    """On a fresh DB, net-worth should return zeros and an empty breakdown."""
    invoke("init")
    result = invoke("net-worth")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["net_worth"] == 0.0
    assert payload["assets_total"] == 0.0
    assert payload["liabilities_total"] == 0.0
    assert payload["account_count"] == 0
    assert payload["breakdown"] == []
    assert payload["oldest_balance_as_of"] is None


def test_networth_with_accounts_no_balances(invoke) -> None:
    """Accounts with no balance_history entries contribute zero."""
    invoke("init")
    invoke("account", "add", "--name", "chase", "--institution", "Chase", "--type", "checking")
    result = invoke("net-worth")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["account_count"] == 1
    assert payload["net_worth"] == 0.0
    assert len(payload["breakdown"]) == 1
    assert payload["breakdown"][0]["balance"] is None


def test_networth_phase4_success_criterion(invoke) -> None:
    """End-to-end: init → add accounts → set balances → net-worth is correct.

    Phase 4 success criterion: `finance init && account add && balance set &&
    net-worth` returns a correct answer.

    Assets:      chase checking   $5,000
                 ally savings    $12,000
                 fidelity 401k   $60,000
    Liabilities: amex credit    -$ 1,200  (stored as +1200, flipped by net-worth)
                 sallie student -$ 8,000

    Expected net worth: 77,000 - 9,200 = 67,800
    """
    invoke("init")

    # Accounts
    invoke("account", "add", "--name", "chase", "--institution", "Chase", "--type", "checking")
    invoke("account", "add", "--name", "ally", "--institution", "Ally", "--type", "savings")
    invoke("account", "add", "--name", "fidelity_401k", "--institution", "Fidelity", "--type", "retirement")
    invoke("account", "add", "--name", "amex", "--institution", "Amex", "--type", "credit_card")
    invoke("account", "add", "--name", "sallie", "--institution", "Sallie Mae", "--type", "loan")

    # Balances (all dated the same so "oldest" is predictable)
    invoke("balance", "set", "--account", "chase", "--balance", "5000", "--as-of", "2026-04-01")
    invoke("balance", "set", "--account", "ally", "--balance", "12000", "--as-of", "2026-04-01")
    invoke("balance", "set", "--account", "fidelity_401k", "--balance", "60000", "--as-of", "2026-04-01")
    invoke("balance", "set", "--account", "amex", "--balance", "1200", "--as-of", "2026-04-01")
    invoke("balance", "set", "--account", "sallie", "--balance", "8000", "--as-of", "2026-04-01")

    result = invoke("net-worth")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)

    assert payload["ok"] is True
    assert payload["account_count"] == 5
    assert payload["assets_total"] == 77000.0
    assert payload["liabilities_total"] == 9200.0
    assert payload["net_worth"] == 67800.0
    assert payload["oldest_balance_as_of"] == "2026-04-01"

    # Each liability contributes a negative signed amount.
    by_name = {b["account"]: b for b in payload["breakdown"]}
    assert by_name["amex"]["signed_contribution"] == -1200.0
    assert by_name["sallie"]["signed_contribution"] == -8000.0
    assert by_name["chase"]["signed_contribution"] == 5000.0


def test_networth_as_of_uses_historical_balance(invoke) -> None:
    """`--as-of` caps which balance row is used per account."""
    invoke("init")
    invoke("account", "add", "--name", "chase", "--institution", "Chase", "--type", "checking")
    invoke("balance", "set", "--account", "chase", "--balance", "1000", "--as-of", "2026-01-01")
    invoke("balance", "set", "--account", "chase", "--balance", "5000", "--as-of", "2026-04-01")

    # As of Feb 1, only the Jan snapshot exists.
    result = invoke("net-worth", "--as-of", "2026-02-01")
    payload = json.loads(result.output)
    assert payload["net_worth"] == 1000.0

    # As of today (default), the Apr snapshot dominates.
    result = invoke("net-worth")
    payload = json.loads(result.output)
    assert payload["net_worth"] == 5000.0


def test_networth_closed_accounts_excluded(invoke) -> None:
    """Closed accounts are not included in net-worth."""
    invoke("init")
    invoke("account", "add", "--name", "chase", "--institution", "Chase", "--type", "checking")
    invoke("account", "add", "--name", "old_amex", "--institution", "Amex", "--type", "credit_card")
    invoke("balance", "set", "--account", "chase", "--balance", "5000", "--as-of", "2026-04-01")
    invoke("balance", "set", "--account", "old_amex", "--balance", "300", "--as-of", "2026-04-01")
    invoke("account", "close", "old_amex")

    result = invoke("net-worth")
    payload = json.loads(result.output)
    # Only the open checking account counts; the closed card is ignored.
    assert payload["net_worth"] == 5000.0
    assert payload["account_count"] == 1
