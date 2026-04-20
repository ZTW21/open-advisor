"""FastAPI dependency injection — DB connection and config."""

from __future__ import annotations

import sqlite3
from typing import Iterator

from finance_advisor.config import Config, resolve_config
from finance_advisor.db import connect

# Resolved once at app startup; overridden in tests.
_config: Config | None = None
_db_override: str | None = None


def configure(db_override: str | None = None) -> None:
    """Call once at startup to resolve and cache the config."""
    global _config, _db_override
    _db_override = db_override
    _config = resolve_config(db_override)


def get_config() -> Config:
    if _config is None:
        configure(_db_override)
    return _config  # type: ignore[return-value]


def get_db() -> Iterator[sqlite3.Connection]:
    """Yield a DB connection, closing it when the request ends.

    Uses check_same_thread=False because FastAPI runs sync endpoints
    in a thread pool — the connection may be created in one thread and
    used in the worker thread. Each request gets its own connection so
    there is no actual cross-thread sharing.
    """
    cfg = get_config()
    conn = sqlite3.connect(str(cfg.db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
    finally:
        conn.close()
