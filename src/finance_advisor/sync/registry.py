"""Registry of sync adapters.

Why a registry instead of hardcoding the three built-ins:

  - The advisor is open-source. A user who builds a YNAB, Monarch, Beancount,
    or custom-bank adapter should be able to register it from a plugin
    module without editing this package.
  - `finance sync --list` needs a single place to enumerate options.
  - Tests can register a fake adapter for isolation.

Built-ins are registered at import time. Third-party code can call
`register(name, cls)` to add more. Names are lowercase with underscores
(`csv_inbox`, not `CSV-Inbox`).
"""

from __future__ import annotations

from typing import Type

from finance_advisor.sync.base import SyncAdapter
from finance_advisor.sync.csv_inbox import CsvInboxAdapter
from finance_advisor.sync.plaid_stub import PlaidAdapter
from finance_advisor.sync.simplefin_stub import SimpleFinAdapter


_REGISTRY: dict[str, Type[SyncAdapter]] = {}


def register(name: str, cls: Type[SyncAdapter]) -> None:
    """Register an adapter class under `name`.

    Overwrites any prior registration — last writer wins. Tests and
    plugins can use this to inject adapters without patching the module.
    """
    if not isinstance(name, str) or not name:
        raise ValueError("adapter name must be a non-empty string")
    if not (isinstance(cls, type) and issubclass(cls, SyncAdapter)):
        raise TypeError(f"{cls!r} is not a SyncAdapter subclass")
    _REGISTRY[name] = cls


def get_adapter(name: str) -> Type[SyncAdapter]:
    """Return the adapter class registered under `name`.

    Raises KeyError with a helpful message listing available names.
    """
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY)) or "(none)"
        raise KeyError(
            f"no sync adapter named {name!r}; available: {available}"
        )
    return _REGISTRY[name]


def list_adapters() -> list[dict]:
    """Return metadata for every registered adapter, sorted by name.

    Shape: [{"name": str, "description": str}].
    Used by `finance sync --list`.
    """
    rows = []
    for name in sorted(_REGISTRY):
        cls = _REGISTRY[name]
        rows.append({
            "name": name,
            "description": getattr(cls, "description", "") or "",
        })
    return rows


# ---- built-in registrations ----
# Done at import time so `finance_advisor.sync` is usable out of the box.
register("csv_inbox", CsvInboxAdapter)
register("simplefin", SimpleFinAdapter)
register("plaid", PlaidAdapter)
