"""The default 'sync' adapter: inventory whatever's already in inbox/.

The manual flow is: user downloads a CSV/OFX from their bank's website and
drops it in `transactions/inbox/`. That's it. This adapter doesn't fetch
anything — it just treats the folder's current contents as the sync result
so the rest of the pipeline (dry-run, import, report) can run uniformly.

This exists so:

  1. `finance sync` always works, even with zero configuration.
  2. Scheduled routines can call `finance sync && finance import` without
     branching on whether a network adapter is installed.
  3. Users who never set up SimpleFIN / Plaid see a consistent UX.

We deliberately do NOT move, delete, or rename files here. The import
pipeline's dedup logic handles replays.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from finance_advisor.sync.base import (
    RemoteAccount,
    SyncAdapter,
    SyncResult,
)


# File extensions the existing importers know how to handle.
# Anything else in inbox/ is ignored (e.g., .DS_Store, notes.txt).
_SUPPORTED_SUFFIXES = {".csv", ".ofx", ".qfx"}


class CsvInboxAdapter(SyncAdapter):
    """Inventories `transactions/inbox/` without touching the network."""

    name = "csv_inbox"
    description = (
        "Manual file drop (default). Inventories transactions/inbox/ "
        "for the importer to pick up. No credentials, no network."
    )

    def list_accounts(self) -> list[RemoteAccount]:
        """We don't know which account a loose CSV belongs to.

        Returning an empty list is the honest answer — the user supplies
        `--account <local_name>` at `finance import` time. If we later
        want per-file account hints (via a sidecar JSON or folder
        convention), that belongs here, not in the importer.
        """
        return []

    def fetch_since(
        self,
        since: date,
        *,
        account_ids: list[str] | None = None,
    ) -> SyncResult:
        """Report existing files in inbox/ as the 'sync result'.

        `since` and `account_ids` are accepted for interface parity but
        don't filter — we can't know the transaction dates inside a file
        without parsing it, and date-level filtering is the importer's
        job, not the sync adapter's.
        """
        result = SyncResult(adapter=self.name)

        inbox = self.inbox_dir
        if not inbox.exists():
            # An uninitialized finance dir. Not an error — just empty.
            result.skipped.append({
                "reason": "inbox_missing",
                "detail": f"{inbox} does not exist",
            })
            return result

        for path in sorted(inbox.iterdir()):
            if not path.is_file():
                continue
            if path.suffix.lower() not in _SUPPORTED_SUFFIXES:
                result.skipped.append({
                    "reason": "unsupported_extension",
                    "detail": path.name,
                })
                continue
            result.files_written.append(path)

        # This adapter doesn't create accounts or know row counts without
        # parsing. Those stay at their defaults (0). The import step will
        # surface the real per-file numbers.
        return result

    @staticmethod
    def _path_key(p: Path) -> tuple:
        """Stable ordering — useful for deterministic test output."""
        return (p.suffix.lower(), p.name)
