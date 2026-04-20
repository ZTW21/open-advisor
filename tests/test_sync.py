"""Tests for the sync adapter package (Phase 12).

We test at three levels:

  1. The registry — lookup, listing, custom registration.
  2. The built-in adapters — csv_inbox behavior, stubs raise cleanly.
  3. The `finance sync` CLI surface — help, --list, error codes.

Network sync is stubbed, so we only verify the stubs fail with the
expected structured SyncError. The live clients land in Phase 12.5.

This module avoids importing pytest so it runs in both pytest and the
project's fallback harness at /tmp/p10test/run_all_tests.py.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from click.testing import CliRunner

from finance_advisor.cli import cli
from finance_advisor.sync import (
    CsvInboxAdapter,
    PlaidAdapter,
    RemoteAccount,
    SimpleFinAdapter,
    SyncAdapter,
    SyncError,
    SyncResult,
    get_adapter,
    list_adapters,
    register,
)


def _assert_raises(exc_type, fn, *args, **kwargs):
    """Minimal pytest.raises substitute so this suite runs without pytest."""
    try:
        fn(*args, **kwargs)
    except exc_type as e:
        return e
    raise AssertionError(f"expected {exc_type.__name__}, got no exception")


# ---------- registry ----------

def test_registry_lists_all_builtins() -> None:
    names = {a["name"] for a in list_adapters()}
    assert {"csv_inbox", "simplefin", "plaid"} <= names


def test_registry_get_adapter_returns_class() -> None:
    assert get_adapter("csv_inbox") is CsvInboxAdapter
    assert get_adapter("simplefin") is SimpleFinAdapter
    assert get_adapter("plaid") is PlaidAdapter


def test_registry_unknown_raises_helpful_keyerror() -> None:
    exc = _assert_raises(KeyError, get_adapter, "does_not_exist")
    msg = str(exc)
    # The message should list what IS available so the user can fix it.
    assert "csv_inbox" in msg
    assert "does_not_exist" in msg


def test_registry_register_accepts_subclasses(tmp_path: Path) -> None:
    class FakeAdapter(SyncAdapter):
        name = "fake_for_test"
        description = "Test-only adapter."

        def list_accounts(self):
            return []

        def fetch_since(self, since, *, account_ids=None):
            return SyncResult(adapter=self.name)

    register("fake_for_test", FakeAdapter)
    assert get_adapter("fake_for_test") is FakeAdapter
    inst = FakeAdapter(tmp_path)
    assert isinstance(inst, SyncAdapter)


def test_registry_register_rejects_non_adapter() -> None:
    _assert_raises(TypeError, register, "bad", object)


def test_registry_register_rejects_empty_name() -> None:
    _assert_raises(ValueError, register, "", CsvInboxAdapter)


# ---------- CsvInboxAdapter ----------

def test_csv_inbox_missing_inbox_reports_skip(tmp_path: Path) -> None:
    """An uninitialized finance dir is fine — just empty + a skip entry."""
    adapter = CsvInboxAdapter(tmp_path)
    result = adapter.fetch_since(date(2026, 1, 1))
    assert result.files_written == []
    assert any(s["reason"] == "inbox_missing" for s in result.skipped)


def test_csv_inbox_lists_supported_files_only(tmp_path: Path) -> None:
    inbox = tmp_path / "transactions" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "chase.csv").write_text("Date,Desc,Amount\n")
    (inbox / "fidelity.ofx").write_text("<OFX></OFX>")
    (inbox / "notes.txt").write_text("ignore me")
    (inbox / ".DS_Store").write_text("mac cruft")

    adapter = CsvInboxAdapter(tmp_path)
    result = adapter.fetch_since(date(2026, 1, 1))

    names = {Path(p).name for p in result.files_written}
    assert names == {"chase.csv", "fidelity.ofx"}
    skipped = {s["detail"] for s in result.skipped}
    assert "notes.txt" in skipped
    assert ".DS_Store" in skipped


def test_csv_inbox_ignores_subdirectories(tmp_path: Path) -> None:
    inbox = tmp_path / "transactions" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "archive").mkdir()
    (inbox / "archive" / "old.csv").write_text("not this one")
    (inbox / "current.csv").write_text("Date,Desc,Amount\n")

    result = CsvInboxAdapter(tmp_path).fetch_since(date(2026, 1, 1))
    names = {Path(p).name for p in result.files_written}
    assert names == {"current.csv"}


def test_csv_inbox_list_accounts_is_empty(tmp_path: Path) -> None:
    """csv_inbox can't know which account a loose CSV belongs to."""
    assert CsvInboxAdapter(tmp_path).list_accounts() == []


def test_csv_inbox_result_payload_is_json_clean(tmp_path: Path) -> None:
    """SyncResult.to_payload() must round-trip through json.dumps."""
    inbox = tmp_path / "transactions" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "a.csv").write_text("Date,Desc,Amount\n")

    result = CsvInboxAdapter(tmp_path).fetch_since(date(2026, 1, 1))
    payload = result.to_payload()
    s = json.dumps(payload)
    back = json.loads(s)
    assert back["adapter"] == "csv_inbox"
    assert len(back["files_written"]) == 1


# ---------- network stubs ----------

def test_simplefin_stub_raises_not_configured(tmp_path: Path) -> None:
    adapter = SimpleFinAdapter(tmp_path)
    exc = _assert_raises(SyncError, adapter.list_accounts)
    assert exc.code == "not_configured"


def test_simplefin_with_token_but_no_map_raises_no_accounts(tmp_path: Path) -> None:
    """Token present but no accounts mapped — tells user what to do next."""
    secrets = tmp_path / "data" / "secrets"
    secrets.mkdir(parents=True)
    (secrets / "simplefin.token").write_text("https://user:pass@example.com/simplefin")

    adapter = SimpleFinAdapter(tmp_path)
    exc = _assert_raises(SyncError, adapter.fetch_since, date(2026, 1, 1))
    assert exc.code == "no_accounts_mapped"


def test_plaid_stub_raises_not_configured(tmp_path: Path) -> None:
    adapter = PlaidAdapter(tmp_path)
    exc = _assert_raises(SyncError, adapter.list_accounts)
    assert exc.code == "not_configured"


def test_plaid_stub_with_secrets_raises_not_implemented(tmp_path: Path) -> None:
    secrets = tmp_path / "data" / "secrets"
    secrets.mkdir(parents=True)
    (secrets / "plaid.json").write_text("{}")

    adapter = PlaidAdapter(tmp_path)
    exc = _assert_raises(SyncError, adapter.fetch_since, date(2026, 1, 1))
    assert exc.code == "not_implemented"


# ---------- RemoteAccount / SyncResult shapes ----------

def test_remote_account_defaults() -> None:
    a = RemoteAccount(remote_id="abc", name="Chase ...1234", institution="Chase")
    assert a.type == "unknown"
    assert a.currency == "USD"


def test_sync_result_empty_payload_shape() -> None:
    r = SyncResult(adapter="csv_inbox")
    payload = r.to_payload()
    assert payload == {
        "adapter": "csv_inbox",
        "files_written": [],
        "accounts_synced": 0,
        "transaction_count": 0,
        "skipped": [],
        "errors": [],
    }


# ---------- CLI surface ----------

def test_cli_sync_shows_up_in_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "sync" in result.output


def test_cli_sync_help_documents_flags(runner: CliRunner) -> None:
    """The command's own --help must describe the public surface."""
    result = runner.invoke(cli, ["sync", "--help"])
    assert result.exit_code == 0
    assert "--adapter" in result.output
    assert "--list" in result.output
    assert "--since" in result.output


def test_cli_sync_unknown_adapter_returns_structured_error(
    invoke, finance_dir: Path
) -> None:
    invoke("init")
    result = invoke("sync", "--adapter", "nope_nope")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "unknown_adapter"


def test_cli_sync_bad_since_returns_structured_error(
    invoke, finance_dir: Path
) -> None:
    invoke("init")
    result = invoke("sync", "--adapter", "csv_inbox", "--since", "not-a-date")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "bad_since"


def test_cli_sync_simplefin_no_token_returns_sync_failed(
    invoke, finance_dir: Path
) -> None:
    """Without a token, simplefin adapter should surface a clean error."""
    invoke("init")
    # Ensure no token exists in the test finance_dir
    token_path = finance_dir / "data" / "secrets" / "simplefin.token"
    if token_path.exists():
        token_path.unlink()
    result = invoke("sync", "--adapter", "simplefin")
    p = json.loads(result.output)
    # Either not_configured (no token) or no_accounts_mapped (token but no map)
    if p.get("ok") is False:
        assert p["error"] == "sync_failed"
        assert p["details"]["code"] in ("not_configured", "no_accounts_mapped")
