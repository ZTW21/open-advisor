"""Tests for the SimpleFIN adapter and client.

Uses mocked HTTP responses — never hits the real SimpleFIN API.
"""

from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from finance_advisor.sync.base import SyncError
from finance_advisor.sync.simplefin_client import (
    claim_token,
    fetch_accounts,
    parse_transaction_date,
    _parse_access_url,
    _date_to_epoch,
)
from finance_advisor.sync.simplefin_stub import SimpleFinAdapter


# ---------- helpers ----------


def _mock_urlopen(response_body: str | bytes, status: int = 200):
    """Return a mock for urllib.request.urlopen."""
    if isinstance(response_body, str):
        response_body = response_body.encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_body
    mock_resp.status = status
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


SAMPLE_ACCOUNTS_RESPONSE = {
    "errors": [],
    "errlist": [],
    "connections": [
        {
            "conn_id": "conn-1",
            "name": "Chase Bank",
            "org_id": "chase",
            "sfin_url": "https://bridge.simplefin.org",
        },
        {
            "conn_id": "conn-2",
            "name": "American Express",
            "org_id": "amex",
            "sfin_url": "https://bridge.simplefin.org",
        },
    ],
    "accounts": [
        {
            "id": "ACT-001",
            "name": "Chase Checking ****1234",
            "conn_id": "conn-1",
            "currency": "USD",
            "balance": "5432.10",
            "balance-date": 1713484800,
            "transactions": [
                {
                    "id": "txn-1",
                    "posted": 1713398400,
                    "amount": "-45.99",
                    "description": "GROCERY STORE #1234",
                },
                {
                    "id": "txn-2",
                    "posted": 1713312000,
                    "amount": "2500.00",
                    "description": "DIRECT DEPOSIT ACME CORP",
                },
                {
                    "id": "txn-3",
                    "posted": 1713225600,
                    "amount": "-12.50",
                    "description": "COFFEE SHOP",
                },
            ],
        },
        {
            "id": "ACT-002",
            "name": "Amex Platinum ****5678",
            "conn_id": "conn-2",
            "currency": "USD",
            "balance": "-1250.00",
            "balance-date": 1713484800,
            "transactions": [
                {
                    "id": "txn-4",
                    "posted": 1713398400,
                    "amount": "-89.00",
                    "description": "RESTAURANT DOWNTOWN",
                },
            ],
        },
    ],
}

ACCESS_URL = "https://demouser:demopass@bridge.simplefin.org/simplefin"


# ---------- client tests ----------


class TestClaimToken:
    def test_happy_path(self):
        import base64
        setup_token = base64.b64encode(
            b"https://bridge.simplefin.org/simplefin/claim/demo"
        ).decode()

        with patch("urllib.request.urlopen", return_value=_mock_urlopen(ACCESS_URL)):
            result = claim_token(setup_token)

        assert result == ACCESS_URL

    def test_already_claimed_raises(self):
        import base64
        import urllib.error

        setup_token = base64.b64encode(
            b"https://bridge.simplefin.org/simplefin/claim/demo"
        ).decode()

        mock_error = urllib.error.HTTPError(
            url="", code=403, msg="Forbidden", hdrs={}, fp=BytesIO(b"")
        )
        with patch("urllib.request.urlopen", side_effect=mock_error):
            with pytest.raises(SyncError) as exc_info:
                claim_token(setup_token)
            assert exc_info.value.code == "token_claimed"

    def test_bad_base64_raises(self):
        with pytest.raises(SyncError) as exc_info:
            claim_token("not-valid-base64!!!")
        assert exc_info.value.code == "bad_token"

    def test_decoded_not_url_raises(self):
        import base64
        setup_token = base64.b64encode(b"just some text").decode()

        with pytest.raises(SyncError) as exc_info:
            claim_token(setup_token)
        assert exc_info.value.code == "bad_token"


class TestParseAccessUrl:
    def test_valid_url(self):
        base, user, password = _parse_access_url(ACCESS_URL)
        assert base == "https://bridge.simplefin.org/simplefin"
        assert user == "demouser"
        assert password == "demopass"

    def test_missing_creds_raises(self):
        with pytest.raises(SyncError) as exc_info:
            _parse_access_url("https://bridge.simplefin.org/simplefin")
        assert exc_info.value.code == "bad_token"


class TestFetchAccounts:
    def test_parses_response(self):
        body = json.dumps(SAMPLE_ACCOUNTS_RESPONSE)

        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
            result = fetch_accounts(ACCESS_URL, start_date=date(2024, 4, 1))

        assert len(result["accounts"]) == 2
        assert result["accounts"][0]["id"] == "ACT-001"
        assert len(result["accounts"][0]["transactions"]) == 3

    def test_auth_failed_raises(self):
        import urllib.error

        mock_error = urllib.error.HTTPError(
            url="", code=403, msg="Forbidden", hdrs={}, fp=BytesIO(b"")
        )
        with patch("urllib.request.urlopen", side_effect=mock_error):
            with pytest.raises(SyncError) as exc_info:
                fetch_accounts(ACCESS_URL)
            assert exc_info.value.code == "auth_failed"

    def test_payment_required_raises(self):
        import urllib.error

        mock_error = urllib.error.HTTPError(
            url="", code=402, msg="Payment Required", hdrs={}, fp=BytesIO(b"")
        )
        with patch("urllib.request.urlopen", side_effect=mock_error):
            with pytest.raises(SyncError) as exc_info:
                fetch_accounts(ACCESS_URL)
            assert exc_info.value.code == "payment_required"


class TestParseTransactionDate:
    def test_normal_epoch(self):
        # 2024-04-18 00:00:00 UTC
        assert parse_transaction_date(1713398400) == "2024-04-18"

    def test_zero_returns_empty(self):
        assert parse_transaction_date(0) == ""


class TestDateToEpoch:
    def test_date_conversion(self):
        d = date(2024, 4, 18)
        epoch = _date_to_epoch(d)
        # Verify round-trip
        dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
        assert dt.date() == d


# ---------- adapter tests ----------


@pytest.fixture
def adapter_dir(tmp_path: Path) -> Path:
    """Set up a directory with SimpleFIN configured."""
    secrets = tmp_path / "data" / "secrets"
    secrets.mkdir(parents=True)
    (secrets / "simplefin.token").write_text(ACCESS_URL + "\n")

    sync_dir = tmp_path / "data" / "sync"
    sync_dir.mkdir(parents=True)

    inbox = tmp_path / "transactions" / "inbox"
    inbox.mkdir(parents=True)

    return tmp_path


class TestSimpleFinAdapterListAccounts:
    def test_returns_remote_accounts(self, adapter_dir):
        adapter = SimpleFinAdapter(adapter_dir)
        body = json.dumps(SAMPLE_ACCOUNTS_RESPONSE)

        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
            accounts = adapter.list_accounts()

        assert len(accounts) == 2
        assert accounts[0].remote_id == "ACT-001"
        assert accounts[0].name == "Chase Checking ****1234"
        assert accounts[0].institution == "Chase Bank"
        assert accounts[1].remote_id == "ACT-002"
        assert accounts[1].institution == "American Express"

    def test_not_configured_raises(self, tmp_path):
        adapter = SimpleFinAdapter(tmp_path)
        with pytest.raises(SyncError) as exc_info:
            adapter.list_accounts()
        assert exc_info.value.code == "not_configured"


class TestSimpleFinAdapterFetchSince:
    def test_writes_csvs(self, adapter_dir):
        adapter = SimpleFinAdapter(adapter_dir)

        # Set up account mapping
        mapping = {"ACT-001": "chase_checking", "ACT-002": "amex_platinum"}
        adapter._save_account_map(mapping)

        body = json.dumps(SAMPLE_ACCOUNTS_RESPONSE)
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
            result = adapter.fetch_since(date(2024, 4, 1))

        assert result.accounts_synced == 2
        assert result.transaction_count == 4
        assert len(result.files_written) == 2

        # Verify CSV content for chase_checking
        chase_csv = [f for f in result.files_written if "chase_checking" in f.name][0]
        with open(chase_csv) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 3
        assert rows[0]["Description"] == "GROCERY STORE #1234"
        assert rows[0]["Amount"] == "-45.99"
        assert rows[1]["Amount"] == "2500.00"

    def test_no_map_raises(self, adapter_dir):
        adapter = SimpleFinAdapter(adapter_dir)
        with pytest.raises(SyncError) as exc_info:
            adapter.fetch_since(date(2024, 4, 1))
        assert exc_info.value.code == "no_accounts_mapped"

    def test_unmapped_accounts_skipped(self, adapter_dir):
        adapter = SimpleFinAdapter(adapter_dir)
        # Only map one of the two accounts
        adapter._save_account_map({"ACT-001": "chase_checking"})

        body = json.dumps(SAMPLE_ACCOUNTS_RESPONSE)
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
            result = adapter.fetch_since(date(2024, 4, 1))

        assert result.accounts_synced == 1
        assert len(result.files_written) == 1

    def test_updates_state(self, adapter_dir):
        adapter = SimpleFinAdapter(adapter_dir)
        adapter._save_account_map({"ACT-001": "chase_checking"})

        body = json.dumps(SAMPLE_ACCOUNTS_RESPONSE)
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
            adapter.fetch_since(date(2024, 4, 1))

        state = adapter._load_state()
        assert "ACT-001" in state
        assert state["ACT-001"] == date.today().isoformat()

    def test_empty_transactions_skipped(self, adapter_dir):
        adapter = SimpleFinAdapter(adapter_dir)
        adapter._save_account_map({"ACT-001": "chase_checking"})

        data = {
            "errors": [],
            "errlist": [],
            "connections": [],
            "accounts": [
                {
                    "id": "ACT-001",
                    "name": "Chase",
                    "currency": "USD",
                    "balance": "100",
                    "transactions": [],
                }
            ],
        }
        body = json.dumps(data)
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
            result = adapter.fetch_since(date(2024, 4, 1))

        assert result.accounts_synced == 0
        assert len(result.files_written) == 0
        assert len(result.skipped) == 1
        assert result.skipped[0]["reason"] == "no_transactions"

    def test_api_errors_surfaced(self, adapter_dir):
        adapter = SimpleFinAdapter(adapter_dir)
        adapter._save_account_map({"ACT-001": "chase_checking"})

        data = {
            "errors": [],
            "errlist": [{"code": "con.auth", "msg": "Login failed", "conn_id": "conn-1"}],
            "connections": [],
            "accounts": [],
        }
        body = json.dumps(data)
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
            result = adapter.fetch_since(date(2024, 4, 1))

        assert len(result.errors) == 1
        assert result.errors[0]["code"] == "con.auth"


class TestAccountMapping:
    def test_save_and_load(self, adapter_dir):
        adapter = SimpleFinAdapter(adapter_dir)
        adapter._save_account_map({"ACT-001": "checking", "ACT-002": "credit"})
        loaded = adapter._load_account_map()
        assert loaded == {"ACT-001": "checking", "ACT-002": "credit"}

    def test_empty_map(self, tmp_path):
        adapter = SimpleFinAdapter(tmp_path)
        assert adapter._load_account_map() == {}


class TestLastSyncedSince:
    def test_returns_oldest_date(self, adapter_dir):
        adapter = SimpleFinAdapter(adapter_dir)
        adapter._save_account_map({"ACT-001": "checking", "ACT-002": "credit"})
        adapter._save_state({
            "ACT-001": "2024-04-15",
            "ACT-002": "2024-04-10",
        })
        assert adapter.last_synced_since() == date(2024, 4, 10)

    def test_no_state_returns_none(self, adapter_dir):
        adapter = SimpleFinAdapter(adapter_dir)
        adapter._save_account_map({"ACT-001": "checking"})
        assert adapter.last_synced_since() is None

    def test_no_map_returns_none(self, adapter_dir):
        adapter = SimpleFinAdapter(adapter_dir)
        assert adapter.last_synced_since() is None


class TestCsvRoundTrip:
    """Verify that CSVs written by the adapter parse correctly with csv_importer."""

    def test_csv_parseable(self, adapter_dir):
        from finance_advisor.importers.csv_importer import parse_csv

        adapter = SimpleFinAdapter(adapter_dir)
        adapter._save_account_map({"ACT-001": "chase_checking"})

        body = json.dumps(SAMPLE_ACCOUNTS_RESPONSE)
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
            result = adapter.fetch_since(date(2024, 4, 1))

        assert len(result.files_written) == 1
        csv_path = result.files_written[0]

        # Parse with the real csv_importer
        parsed = parse_csv(csv_path)
        assert len(parsed) == 3

        # Verify amounts match (sign convention: positive=inflow, negative=outflow)
        amounts = [r.amount for r in parsed]
        assert -45.99 in amounts
        assert 2500.0 in amounts
        assert -12.5 in amounts

        # Verify descriptions
        descs = [r.description for r in parsed]
        assert "GROCERY STORE #1234" in descs
        assert "DIRECT DEPOSIT ACME CORP" in descs
