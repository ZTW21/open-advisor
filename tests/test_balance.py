"""Tests for `finance balance set` and `finance balance list`.

The core contract for `balance set`:
  - Idempotent on (account, as_of_date) — second call updates, not duplicates.
  - Accepts YYYY-MM-DD; validates format and calendar validity.
  - Missing account surfaces account_not_found.

`balance list` supports --account, --since, --limit filters and returns
rows ordered by account, then date DESC.
"""

from __future__ import annotations

import json


def _seed_accounts(invoke) -> None:
    invoke("init")
    invoke(
        "account", "add",
        "--name", "chase",
        "--institution", "Chase",
        "--type", "checking",
    )
    invoke(
        "account", "add",
        "--name", "amex",
        "--institution", "Amex",
        "--type", "credit_card",
    )


def test_balance_set_inserts(invoke) -> None:
    _seed_accounts(invoke)
    result = invoke(
        "balance", "set",
        "--account", "chase",
        "--balance", "5000.00",
        "--as-of", "2026-04-01",
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["action"] == "inserted"
    assert payload["balance"] == 5000.00
    assert payload["as_of_date"] == "2026-04-01"
    assert payload["source"] == "manual"
    assert payload["previous"] is None


def test_balance_set_idempotent(invoke) -> None:
    """Calling set twice on the same (account, date) updates, not duplicates."""
    _seed_accounts(invoke)
    invoke(
        "balance", "set",
        "--account", "chase",
        "--balance", "5000.00",
        "--as-of", "2026-04-01",
    )
    result = invoke(
        "balance", "set",
        "--account", "chase",
        "--balance", "5250.00",
        "--as-of", "2026-04-01",
        "--source", "reconcile",
    )
    payload = json.loads(result.output)
    assert payload["action"] == "updated"
    assert payload["balance"] == 5250.00
    assert payload["previous"] == {"balance": 5000.00, "source": "manual"}

    # Only one snapshot should exist for that date.
    listed = invoke("balance", "list", "--account", "chase")
    listed_payload = json.loads(listed.output)
    assert listed_payload["count"] == 1


def test_balance_set_unknown_account(invoke) -> None:
    invoke("init")
    result = invoke(
        "balance", "set",
        "--account", "ghost",
        "--balance", "100",
        "--as-of", "2026-04-01",
    )
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"] == "account_not_found"


def test_balance_set_bad_date(invoke) -> None:
    _seed_accounts(invoke)
    # Click raises BadParameter → exit_code=2.
    result = invoke(
        "balance", "set",
        "--account", "chase",
        "--balance", "100",
        "--as-of", "04/01/2026",
    )
    assert result.exit_code != 0
    assert "YYYY-MM-DD" in result.output or "YYYY-MM-DD" in (result.stderr or "")


def test_balance_set_impossible_date(invoke) -> None:
    _seed_accounts(invoke)
    # Feb 30 matches the regex but is not a real date.
    result = invoke(
        "balance", "set",
        "--account", "chase",
        "--balance", "100",
        "--as-of", "2026-02-30",
    )
    assert result.exit_code != 0


def test_balance_set_default_date_is_today(invoke) -> None:
    from datetime import date

    _seed_accounts(invoke)
    result = invoke(
        "balance", "set",
        "--account", "chase",
        "--balance", "100",
    )
    payload = json.loads(result.output)
    assert payload["as_of_date"] == date.today().isoformat()


def test_balance_list_empty(invoke) -> None:
    invoke("init")
    result = invoke("balance", "list")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["count"] == 0
    assert payload["snapshots"] == []


def test_balance_list_by_account(invoke) -> None:
    _seed_accounts(invoke)
    invoke("balance", "set", "--account", "chase", "--balance", "5000", "--as-of", "2026-03-01")
    invoke("balance", "set", "--account", "chase", "--balance", "5200", "--as-of", "2026-04-01")
    invoke("balance", "set", "--account", "amex", "--balance", "400", "--as-of", "2026-04-01")

    result = invoke("balance", "list", "--account", "chase")
    payload = json.loads(result.output)
    assert payload["count"] == 2
    dates = [s["as_of_date"] for s in payload["snapshots"]]
    # Ordered DESC per account.
    assert dates == ["2026-04-01", "2026-03-01"]


def test_balance_list_since(invoke) -> None:
    _seed_accounts(invoke)
    invoke("balance", "set", "--account", "chase", "--balance", "5000", "--as-of", "2026-01-01")
    invoke("balance", "set", "--account", "chase", "--balance", "5200", "--as-of", "2026-03-01")
    invoke("balance", "set", "--account", "chase", "--balance", "5400", "--as-of", "2026-04-01")

    result = invoke("balance", "list", "--since", "2026-03-01")
    payload = json.loads(result.output)
    assert payload["count"] == 2
    dates = {s["as_of_date"] for s in payload["snapshots"]}
    assert dates == {"2026-03-01", "2026-04-01"}


def test_balance_list_limit_per_account(invoke) -> None:
    """--limit returns the N most recent snapshots per account."""
    _seed_accounts(invoke)
    for as_of in ("2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01"):
        invoke("balance", "set", "--account", "chase", "--balance", "100", "--as-of", as_of)
        invoke("balance", "set", "--account", "amex", "--balance", "100", "--as-of", as_of)

    result = invoke("balance", "list", "--limit", "2")
    payload = json.loads(result.output)
    # 2 most recent × 2 accounts = 4
    assert payload["count"] == 4
    dates_by_account = {}
    for s in payload["snapshots"]:
        dates_by_account.setdefault(s["account"], []).append(s["as_of_date"])
    for acct, dates in dates_by_account.items():
        assert dates == ["2026-04-01", "2026-03-01"], acct


def test_balance_list_unknown_account(invoke) -> None:
    invoke("init")
    result = invoke("balance", "list", "--account", "ghost")
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"] == "account_not_found"
