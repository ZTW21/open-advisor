"""Tests for `finance account edit` and `finance account close`.

Phase 4 introduced these subcommands. The existing add/list/show subcommands
are exercised indirectly by test_networth.py and test_balance.py.
"""

from __future__ import annotations

import json


def _add_chase(invoke) -> None:
    invoke("init")
    invoke(
        "account", "add",
        "--name", "chase",
        "--institution", "Chase",
        "--type", "checking",
    )


def test_edit_no_flags_errors(invoke) -> None:
    """`account edit` with no flags returns a no_updates error."""
    _add_chase(invoke)
    result = invoke("account", "edit", "chase")
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"] == "no_updates"


def test_edit_rename(invoke) -> None:
    """Renaming an account updates the row and reports the before/after."""
    _add_chase(invoke)
    result = invoke("account", "edit", "chase", "--rename", "chase_checking")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["account"]["name"] == "chase_checking"
    assert payload["changed_fields"]["name"] == {
        "before": "chase", "after": "chase_checking"
    }

    # The old name no longer resolves.
    result = invoke("account", "show", "chase")
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"] == "account_not_found"


def test_edit_rename_conflict(invoke) -> None:
    """Renaming to a name already in use surfaces duplicate_account."""
    _add_chase(invoke)
    invoke(
        "account", "add",
        "--name", "ally",
        "--institution", "Ally",
        "--type", "savings",
    )
    result = invoke("account", "edit", "chase", "--rename", "ally")
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"] == "duplicate_account"


def test_edit_multiple_fields(invoke) -> None:
    """Edit updates only the fields passed; others unchanged."""
    _add_chase(invoke)
    result = invoke(
        "account", "edit", "chase",
        "--institution", "JPMorgan Chase",
        "--notes", "Primary checking",
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert set(payload["changed_fields"]) == {"institution", "notes"}
    assert payload["account"]["account_type"] == "checking"  # unchanged


def test_edit_not_found(invoke) -> None:
    invoke("init")
    result = invoke("account", "edit", "ghost", "--notes", "x")
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"] == "account_not_found"


def test_close_marks_inactive(invoke) -> None:
    """Close flips active to 0 and stamps closed_on."""
    _add_chase(invoke)
    result = invoke("account", "close", "chase", "--on", "2026-04-01")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["already_closed"] is False
    assert payload["account"]["closed_on"] == "2026-04-01"

    show = invoke("account", "show", "chase")
    show_payload = json.loads(show.output)
    assert show_payload["account"]["active"] is False
    assert show_payload["account"]["closed_on"] == "2026-04-01"


def test_close_idempotent(invoke) -> None:
    """Closing an already-closed account is a no-op, flagged already_closed."""
    _add_chase(invoke)
    invoke("account", "close", "chase", "--on", "2026-04-01")
    result = invoke("account", "close", "chase", "--on", "2026-04-02")
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["already_closed"] is True
    # The original closed_on date sticks.
    assert payload["account"]["closed_on"] == "2026-04-01"


def test_close_not_found(invoke) -> None:
    invoke("init")
    result = invoke("account", "close", "ghost")
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"] == "account_not_found"


def test_close_default_date_is_today(invoke) -> None:
    """Without --on, close uses today's ISO date."""
    from datetime import date

    _add_chase(invoke)
    result = invoke("account", "close", "chase")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["account"]["closed_on"] == date.today().isoformat()


def test_list_active_only_excludes_closed(invoke) -> None:
    """`account list --active-only` hides closed accounts."""
    _add_chase(invoke)
    invoke(
        "account", "add",
        "--name", "old_amex",
        "--institution", "Amex",
        "--type", "credit_card",
    )
    invoke("account", "close", "old_amex")

    result = invoke("account", "list", "--active-only")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    names = [a["name"] for a in payload["accounts"]]
    assert "chase" in names
    assert "old_amex" not in names

    # Without --active-only, the closed account reappears.
    result = invoke("account", "list")
    payload = json.loads(result.output)
    names = [a["name"] for a in payload["accounts"]]
    assert "old_amex" in names
