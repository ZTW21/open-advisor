"""Shared types for all sync adapters.

A sync adapter's job is to drop statement files into `transactions/inbox/`
in a format the existing importers (csv, ofx) already understand. Adapters
never touch the database directly — the normal `finance import` pipeline
picks up their output.

This separation matters for two reasons:

1. **Trust boundary.** Fetched-from-network data goes through the same
   parse / normalize / dedup / dry-run path as user-dropped files. A sync
   adapter cannot skip that path; it can only produce files for it.
2. **Degradation.** If sync is broken or not configured, the manual
   drop-a-CSV flow still works. Sync is always optional.

Every adapter implements the `SyncAdapter` ABC. See `csv_inbox.py` for the
minimal default, `simplefin_stub.py` / `plaid_stub.py` for the network
shapes.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


class SyncError(Exception):
    """Raised when an adapter fails in a structured way.

    Adapters should raise this (rather than generic Exception) so the
    `finance sync` command can surface a clean error payload with a stable
    code, e.g. `not_configured`, `auth_failed`, `network_error`,
    `rate_limited`.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class RemoteAccount:
    """An account as reported by a remote provider — before we map it to ours.

    The advisor stores accounts locally with its own `name` (e.g. "chase_checking").
    Providers return their own identifiers. `RemoteAccount` is the unmapped view;
    the sync command is responsible for linking `remote_id` to a local account
    in the database (or reporting an unlinked remote account as a finding).

    Fields:
        remote_id:   provider-stable identifier for the account.
        name:        the provider's human-facing name (often bank + last4).
        institution: bank / broker name the provider reports.
        type:        coarse type hint — "checking", "savings", "credit_card",
                     "brokerage", "loan", or "unknown". Informational only;
                     the local account_type is what drives behavior.
        currency:    ISO 4217 code, default USD.
    """

    remote_id: str
    name: str
    institution: str
    type: str = "unknown"
    currency: str = "USD"


@dataclass
class SyncResult:
    """Outcome of a single `fetch_since` call.

    `files_written` is the list of new files placed in `transactions/inbox/`.
    These files are plain CSV/OFX — they are NOT imported yet. The user (or
    a scheduled routine) still has to run `finance import` to load them.

    `skipped` tracks accounts or date ranges the adapter chose not to fetch
    (already-seen, out-of-scope, unsupported), with a short reason each.
    `errors` tracks soft failures that didn't stop the whole sync — one
    account failed but others succeeded.
    """

    adapter: str
    files_written: list[Path] = field(default_factory=list)
    accounts_synced: int = 0
    transaction_count: int = 0
    skipped: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)

    def to_payload(self) -> dict:
        """Serialize for the --json CLI renderer."""
        return {
            "adapter": self.adapter,
            "files_written": [str(p) for p in self.files_written],
            "accounts_synced": self.accounts_synced,
            "transaction_count": self.transaction_count,
            "skipped": list(self.skipped),
            "errors": list(self.errors),
        }


class SyncAdapter(abc.ABC):
    """The contract every sync adapter satisfies.

    An adapter is constructed with a `finance_dir` (the advisor's root) and
    any adapter-specific config (tokens, account maps). It exposes two
    operations:

      - `list_accounts()` — what the remote sees. Used to help the user
        map remote accounts to local ones. Safe to call repeatedly.
      - `fetch_since(since, ...)` — pull new statements since a given date
        and drop them into `transactions/inbox/` as files. Returns a
        `SyncResult` describing what landed on disk.

    Adapters MUST NOT write to the database. They write files only. The
    normal import pipeline is the only thing allowed to persist
    transactions.
    """

    #: short, stable name used in config and the registry (e.g. "csv_inbox").
    name: str = "base"

    #: human-readable description shown by `finance sync --list`.
    description: str = ""

    def __init__(self, finance_dir: Path, config: dict | None = None) -> None:
        self.finance_dir = Path(finance_dir)
        self.config = dict(config or {})

    @property
    def inbox_dir(self) -> Path:
        """Where this adapter drops files. Always `transactions/inbox/`."""
        return self.finance_dir / "transactions" / "inbox"

    @abc.abstractmethod
    def list_accounts(self) -> list[RemoteAccount]:
        """Return the accounts this adapter can see.

        May raise `SyncError("not_configured", ...)` if credentials are
        missing, or `SyncError("auth_failed", ...)` if they're rejected.
        """

    @abc.abstractmethod
    def fetch_since(
        self,
        since: date,
        *,
        account_ids: list[str] | None = None,
    ) -> SyncResult:
        """Fetch transactions from `since` (inclusive) to today.

        If `account_ids` is None, fetch all accounts the adapter knows about.
        Files written MUST land in `self.inbox_dir`, be named with a prefix
        that identifies the adapter (e.g. `simplefin_<account>_<date>.csv`),
        and be in a format the existing importers can parse.

        Returns a `SyncResult` describing what was written. Does NOT call
        `finance import`; the caller decides when to import.
        """
