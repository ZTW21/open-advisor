"""Plaid adapter — stub.

Plaid offers broader bank coverage than SimpleFIN and a richer data model
(categorized transactions, balance history, auth/identity/investments
endpoints). In exchange:

  - The user must create a Plaid developer account (or use a hosted
    proxy), which carries onboarding friction.
  - Plaid Link requires an OAuth-ish handshake that briefly passes bank
    credentials to Plaid (not to us). Some users find this acceptable;
    some don't.
  - Tokens are scoped per-item and can be revoked per-institution.

We therefore offer Plaid as an *option*, not the default. SimpleFIN is
recommended for most users; Plaid is for users who specifically want it
or whose bank isn't in SimpleFIN's coverage.

This stub is inert. Phase 12.5/13 will wire it in. When it is wired in:

  - Client credentials in `data/secrets/plaid.json` (gitignored; 0600).
  - Per-item access tokens in `data/secrets/plaid_items.json` (0600).
  - Account map in `data/sync/plaid_accounts.json` (tracked).
  - Output format matches existing csv_importer so a single importer
    handles all sources.
"""

from __future__ import annotations

from datetime import date

from finance_advisor.sync.base import (
    RemoteAccount,
    SyncAdapter,
    SyncError,
    SyncResult,
)


class PlaidAdapter(SyncAdapter):
    """Stubbed Plaid adapter. Not configured; never hits the network."""

    name = "plaid"
    description = (
        "Plaid Link — broader bank coverage, richer data, more setup. "
        "NOT YET IMPLEMENTED in this release; will land in Phase 12.5."
    )

    _SECRETS_PATH = "data/secrets/plaid.json"

    def _secrets_path(self):
        return self.finance_dir / self._SECRETS_PATH

    def _check_configured(self) -> None:
        if not self._secrets_path().exists():
            raise SyncError(
                "not_configured",
                (
                    "Plaid is not configured. Network sync lands in "
                    "Phase 12.5. For now, download CSVs from your bank "
                    "and drop them in transactions/inbox/, then use the "
                    "'csv_inbox' adapter (the default). "
                    "If you're weighing sync options, SimpleFIN is simpler "
                    "and read-only by design — consider it first."
                ),
            )
        raise SyncError(
            "not_implemented",
            (
                "Plaid secrets were found at "
                f"{self._SECRETS_PATH}, but the network client is not wired "
                "up in this release. Track Phase 12.5 for the live sync."
            ),
        )

    def list_accounts(self) -> list[RemoteAccount]:
        self._check_configured()
        return []  # unreachable until implemented

    def fetch_since(
        self,
        since: date,
        *,
        account_ids: list[str] | None = None,
    ) -> SyncResult:
        self._check_configured()
        return SyncResult(adapter=self.name)  # unreachable until implemented
