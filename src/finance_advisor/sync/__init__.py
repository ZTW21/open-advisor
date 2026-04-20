"""Pluggable sync adapters — pull statements from the user's banks.

The advisor's main import path is manual: the user drops CSV/OFX files in
`transactions/inbox/` and runs `finance import`. That's the fallback, and it
always works — no credentials, no third-party service, no lock-in.

This package defines an optional *sync layer* that fetches statements
programmatically. Each adapter satisfies the `SyncAdapter` protocol
(`list_accounts`, `fetch_since`) and drops files into `transactions/inbox/`
for the normal import pipeline to consume.

Available adapters:

  - `csv_inbox` (default)  — the manual drop-a-file flow, treated as a
    sync so the UX is uniform. Does not fetch anything; just inventories
    what's already in inbox/. Always works; always safe.
  - `simplefin`            — SimpleFIN Bridge tokens. Read-only by design,
    doesn't require your bank password. Pulls transactions and balances.
    Setup: `finance sync setup-simplefin --token <token>`.
  - `plaid`                — Plaid Link. More banks; requires a Plaid
    account and careful credential handling. Stubbed; client not yet wired.
"""

from __future__ import annotations

from finance_advisor.sync.base import (
    SyncAdapter,
    SyncResult,
    RemoteAccount,
    SyncError,
)
from finance_advisor.sync.csv_inbox import CsvInboxAdapter
from finance_advisor.sync.simplefin_stub import SimpleFinAdapter
from finance_advisor.sync.plaid_stub import PlaidAdapter
from finance_advisor.sync.registry import (
    get_adapter,
    list_adapters,
    register,
)

__all__ = [
    "SyncAdapter",
    "SyncResult",
    "RemoteAccount",
    "SyncError",
    "CsvInboxAdapter",
    "SimpleFinAdapter",
    "PlaidAdapter",
    "get_adapter",
    "list_adapters",
    "register",
]
