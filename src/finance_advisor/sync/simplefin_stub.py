"""SimpleFIN Bridge adapter — stub.

Why SimpleFIN is the preferred network option:

  - Read-only by design. SimpleFIN tokens can fetch transactions; they
    cannot move money, change contact info, or rotate passwords. Even if
    a token leaks, the blast radius is 'attacker can see your transaction
    history' — not 'attacker can drain your account'.
  - Users hold their own credentials. The user authenticates with their
    bank through SimpleFIN Bridge (a service they choose, not us). We
    never see the bank password, and we never proxy it. We only see the
    access token the user copies over.
  - Standard, small format. The JSON payload maps cleanly to our
    ParsedRow shape — an importer is a ~50 line adapter.

This stub is intentionally inert. In Phase 12 we are building the
interface and the scheduling layer; the network implementation lands
later. Calling `fetch_since` raises `SyncError('not_configured', ...)`
unless the user has populated a token — which they can't yet, because
we haven't specified where.

When this adapter is filled in (Phase 12.5/13):
  - Token lives in `data/secrets/simplefin.token` (gitignored; 0600 perms).
  - Account map lives in `data/sync/simplefin_accounts.json` (tracked,
    mapping remote_id -> local account name).
  - Output files: `simplefin_<local_account>_<YYYY-MM-DD>.csv` in inbox/,
    formatted to match the existing `csv_importer` schema so no second
    importer is needed.
"""

from __future__ import annotations

from datetime import date

from finance_advisor.sync.base import (
    RemoteAccount,
    SyncAdapter,
    SyncError,
    SyncResult,
)


class SimpleFinAdapter(SyncAdapter):
    """Stubbed SimpleFIN adapter. Not configured; never hits the network."""

    name = "simplefin"
    description = (
        "SimpleFIN Bridge — read-only bank sync via user-held token. "
        "NOT YET IMPLEMENTED in this release; will land in Phase 12.5."
    )

    # Where the token will live once implemented. Documented here so the
    # error message can point the user at the right place.
    _TOKEN_PATH = "data/secrets/simplefin.token"

    def _token_path(self):
        return self.finance_dir / self._TOKEN_PATH

    def _check_configured(self) -> None:
        if not self._token_path().exists():
            raise SyncError(
                "not_configured",
                (
                    "SimpleFIN is not configured. Network sync lands in "
                    "Phase 12.5. For now, download CSVs from your bank "
                    "and drop them in transactions/inbox/, then use the "
                    "'csv_inbox' adapter (the default)."
                ),
            )
        # Even if a token file exists, Phase 12's stub does not perform
        # network calls. Treat 'configured but unimplemented' distinctly
        # so users aren't surprised.
        raise SyncError(
            "not_implemented",
            (
                "A SimpleFIN token file was found at "
                f"{self._TOKEN_PATH}, but the network client is not wired "
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
