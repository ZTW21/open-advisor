"""Configuration and path resolution.

The CLI expects to run from inside a finance directory. The directory is
identified by the presence of `CLAUDE.md` at its root. If the user has
navigated somewhere else, the CLI walks up until it finds one (bounded).

The SQLite DB lives at `<finance_dir>/data/finance.sqlite` by default.
Users can override via the FINANCE_DB env var or the global --db flag.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


MAX_UPWARD_SEARCH = 6


class FinanceDirError(Exception):
    """Raised when we can't find a finance directory."""


@dataclass(frozen=True)
class Config:
    """Resolved paths for a finance directory."""

    finance_dir: Path
    db_path: Path
    exports_dir: Path
    backups_dir: Path
    inbox_dir: Path
    processed_dir: Path
    reports_dir: Path


def find_finance_dir(start: Path | None = None) -> Path:
    """Walk upward from `start` (or cwd) until we find a `CLAUDE.md`."""
    cursor = (start or Path.cwd()).resolve()
    for _ in range(MAX_UPWARD_SEARCH):
        if (cursor / "CLAUDE.md").is_file():
            return cursor
        if cursor.parent == cursor:
            break
        cursor = cursor.parent
    raise FinanceDirError(
        "Could not find a finance directory (no CLAUDE.md found walking upward). "
        "Run from inside a finance directory, or pass --db explicitly."
    )


def resolve_config(db_override: str | None = None) -> Config:
    """Resolve all the paths the CLI will use.

    Precedence for the DB path:
      1. --db flag (db_override)
      2. FINANCE_DB environment variable
      3. <finance_dir>/data/finance.sqlite
    """
    # 1. Explicit override
    if db_override:
        db_path = Path(db_override).resolve()
        # When using a db override, still try to locate the finance dir from cwd
        # for exports/backups context; fall back to db's parent if we can't.
        try:
            finance_dir = find_finance_dir()
        except FinanceDirError:
            finance_dir = db_path.parent.parent if db_path.parent.name == "data" else db_path.parent
    else:
        # 2. env var
        env_db = os.environ.get("FINANCE_DB")
        if env_db:
            db_path = Path(env_db).resolve()
            try:
                finance_dir = find_finance_dir()
            except FinanceDirError:
                finance_dir = db_path.parent.parent if db_path.parent.name == "data" else db_path.parent
        else:
            # 3. default
            finance_dir = find_finance_dir()
            db_path = finance_dir / "data" / "finance.sqlite"

    return Config(
        finance_dir=finance_dir,
        db_path=db_path,
        exports_dir=finance_dir / "data" / "exports",
        backups_dir=finance_dir / "data" / "backups",
        inbox_dir=finance_dir / "transactions" / "inbox",
        processed_dir=finance_dir / "transactions" / "processed",
        reports_dir=finance_dir / "reports",
    )


def ensure_data_dirs(config: Config) -> None:
    """Create data directories if they don't exist yet. Idempotent."""
    config.db_path.parent.mkdir(parents=True, exist_ok=True)
    config.exports_dir.mkdir(parents=True, exist_ok=True)
    config.backups_dir.mkdir(parents=True, exist_ok=True)
