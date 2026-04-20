"""SimpleFIN Bridge adapter — live implementation.

SimpleFIN is the preferred network sync option:
  - Read-only by design. Tokens can fetch transactions; they cannot move
    money, change contact info, or rotate passwords.
  - Users hold their own credentials. We never see the bank password.
  - Standard JSON format; clean mapping to our CSV import schema.

Setup flow:
  1. User gets a setup token from https://bridge.simplefin.org/simplefin/create
  2. `finance sync setup-simplefin --token <base64>` claims it and stores
     the access URL in `data/secrets/simplefin.token`.
  3. `finance sync --adapter simplefin --list-accounts` shows remote accounts.
  4. `finance sync map --remote-id <id> --account <local>` links them.
  5. `finance sync --adapter simplefin` fetches new transactions.

Files:
  - Token: data/secrets/simplefin.token (gitignored, 0600)
  - Account map: data/sync/simplefin_accounts.json (remote_id → local name)
  - State: data/sync/simplefin_state.json (last-synced timestamps)
  - Output: transactions/inbox/simplefin_<account>_<date>.csv
"""

from __future__ import annotations

import csv
import json
import os
from datetime import date
from pathlib import Path
from typing import Optional

from finance_advisor.sync.base import (
    RemoteAccount,
    SyncAdapter,
    SyncError,
    SyncResult,
)
from finance_advisor.sync.simplefin_client import (
    fetch_accounts,
    parse_transaction_date,
)


class SimpleFinAdapter(SyncAdapter):
    """SimpleFIN Bridge adapter — fetches transactions via the SimpleFIN API."""

    name = "simplefin"
    description = (
        "SimpleFIN Bridge — read-only bank sync via user-held token. "
        "Run `finance sync setup-simplefin --token <token>` to configure."
    )

    TOKEN_REL = "data/secrets/simplefin.token"
    ACCOUNT_MAP_REL = "data/sync/simplefin_accounts.json"
    STATE_REL = "data/sync/simplefin_state.json"

    @property
    def token_path(self) -> Path:
        return self.finance_dir / self.TOKEN_REL

    @property
    def account_map_path(self) -> Path:
        return self.finance_dir / self.ACCOUNT_MAP_REL

    @property
    def state_path(self) -> Path:
        return self.finance_dir / self.STATE_REL

    def _read_access_url(self) -> str:
        if not self.token_path.exists():
            raise SyncError(
                "not_configured",
                "SimpleFIN is not configured. Run:\n"
                "  finance sync setup-simplefin --token <your_setup_token>\n"
                "Get a token at https://bridge.simplefin.org/simplefin/create",
            )
        return self.token_path.read_text().strip()

    def _load_account_map(self) -> dict[str, str]:
        """Load {remote_id: local_account_name} mapping."""
        if not self.account_map_path.exists():
            return {}
        return json.loads(self.account_map_path.read_text())

    def _save_account_map(self, mapping: dict[str, str]) -> None:
        self.account_map_path.parent.mkdir(parents=True, exist_ok=True)
        self.account_map_path.write_text(json.dumps(mapping, indent=2) + "\n")

    def _load_state(self) -> dict[str, str]:
        """Load {remote_id: last_synced_date_iso} state."""
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text())

    def _save_state(self, state: dict[str, str]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2) + "\n")

    def last_synced_since(self) -> Optional[date]:
        """Return the oldest last-synced date across mapped accounts.

        Used by the sync command to default --since when no explicit date
        is given. Returns None if no state exists.
        """
        state = self._load_state()
        account_map = self._load_account_map()
        if not state or not account_map:
            return None
        dates = []
        for remote_id in account_map:
            if remote_id in state:
                try:
                    dates.append(date.fromisoformat(state[remote_id]))
                except ValueError:
                    pass
        return min(dates) if dates else None

    def list_accounts(self) -> list[RemoteAccount]:
        access_url = self._read_access_url()
        data = fetch_accounts(access_url, balances_only=True)

        # Surface any errors from SimpleFIN
        errlist = data.get("errlist", [])
        if errlist:
            # Log but don't fail — partial data is still useful
            pass

        accounts = []
        for acct in data.get("accounts", []):
            # Map SimpleFIN account types
            acct_type = "unknown"
            # SimpleFIN doesn't provide explicit types, but we can infer
            # from balance sign and connection info
            accounts.append(RemoteAccount(
                remote_id=acct["id"],
                name=acct.get("name", "Unknown"),
                institution=_institution_name(data, acct.get("conn_id", "")),
                type=acct_type,
                currency=acct.get("currency", "USD"),
            ))
        return accounts

    def fetch_since(
        self,
        since: date,
        *,
        account_ids: Optional[list[str]] = None,
    ) -> SyncResult:
        access_url = self._read_access_url()
        account_map = self._load_account_map()

        if not account_map:
            raise SyncError(
                "no_accounts_mapped",
                "No accounts are mapped. First run:\n"
                "  finance sync --adapter simplefin --list-accounts\n"
                "Then map each account:\n"
                "  finance sync map --remote-id <id> --account <local_name>",
            )

        # Filter to requested account IDs if specified
        if account_ids:
            fetch_ids = [aid for aid in account_ids if aid in account_map]
        else:
            fetch_ids = list(account_map.keys())

        if not fetch_ids:
            return SyncResult(adapter=self.name)

        data = fetch_accounts(
            access_url,
            start_date=since,
            account_ids=fetch_ids,
            pending=True,
        )

        # Check for API-level errors
        errlist = data.get("errlist", [])

        result = SyncResult(adapter=self.name)
        state = self._load_state()
        remote_accounts = {a["id"]: a for a in data.get("accounts", [])}

        for remote_id in fetch_ids:
            local_name = account_map[remote_id]

            if remote_id not in remote_accounts:
                result.skipped.append({
                    "reason": "not_in_response",
                    "detail": f"Account {remote_id} ({local_name}) not returned by SimpleFIN.",
                })
                continue

            acct = remote_accounts[remote_id]
            transactions = acct.get("transactions", [])

            if not transactions:
                result.skipped.append({
                    "reason": "no_transactions",
                    "detail": f"{local_name}: no transactions since {since.isoformat()}.",
                })
                # Still update state — we checked, there was nothing new
                state[remote_id] = date.today().isoformat()
                continue

            # Write CSV to inbox
            csv_path = self._write_csv(local_name, transactions)
            result.files_written.append(csv_path)
            result.accounts_synced += 1
            result.transaction_count += len(transactions)
            state[remote_id] = date.today().isoformat()

        # Surface SimpleFIN API errors as soft errors
        for err in errlist:
            result.errors.append({
                "code": err.get("code", "unknown"),
                "message": err.get("msg", ""),
                "account_id": err.get("account_id"),
            })

        # Collect balance updates for all accounts in the response
        self._last_balances = {}
        for remote_id in fetch_ids:
            if remote_id in remote_accounts:
                acct = remote_accounts[remote_id]
                balance_str = acct.get("balance")
                balance_date_epoch = acct.get("balance-date", 0)
                if balance_str is not None:
                    balance_date = parse_transaction_date(balance_date_epoch)
                    self._last_balances[account_map[remote_id]] = {
                        "balance": float(balance_str),
                        "as_of_date": balance_date or date.today().isoformat(),
                    }

        self._save_state(state)
        return result

    def get_balance_updates(self) -> dict[str, dict]:
        """Return {local_account_name: {balance, as_of_date}} from the last fetch.

        Call after fetch_since(). The sync command uses this to update
        balance_history in the DB. The adapter itself never writes to the DB.
        """
        return getattr(self, "_last_balances", {})

    def _write_csv(self, local_name: str, transactions: list[dict]) -> Path:
        """Write transactions to a CSV file in the inbox."""
        today = date.today().isoformat()
        filename = f"simplefin_{local_name}_{today}.csv"
        path = self.inbox_dir / filename
        self.inbox_dir.mkdir(parents=True, exist_ok=True)

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Description", "Amount"])
            for txn in transactions:
                posted = txn.get("posted", 0)
                txn_date = parse_transaction_date(posted)
                if not txn_date:
                    # Use transacted_at if posted is 0 (pending)
                    transacted = txn.get("transacted_at", 0)
                    txn_date = parse_transaction_date(transacted)
                if not txn_date:
                    # Skip transactions with no date at all
                    continue
                description = txn.get("description", "").strip()
                amount = txn.get("amount", "0")
                writer.writerow([txn_date, description, amount])

        return path


def _institution_name(data: dict, conn_id: str) -> str:
    """Look up the institution name from the connections list."""
    for conn in data.get("connections", []):
        if conn.get("conn_id") == conn_id:
            return conn.get("name", "Unknown")
    return "Unknown"
