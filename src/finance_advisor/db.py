"""Database connection and migrations.

Migrations live in src/finance_advisor/migrations/NNN_description.sql.
Each migration runs exactly once; schema_version tracks what's been applied.
"""

from __future__ import annotations

import re
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator


MIGRATIONS_DIR = Path(__file__).parent / "migrations"
MIGRATION_FILENAME_RE = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")


def connect(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with sane defaults."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Commit on success, rollback on exception."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def list_migrations() -> list[tuple[int, Path]]:
    """Return [(version, path)] sorted by version."""
    found: list[tuple[int, Path]] = []
    if not MIGRATIONS_DIR.is_dir():
        return found
    for p in sorted(MIGRATIONS_DIR.iterdir()):
        m = MIGRATION_FILENAME_RE.match(p.name)
        if m:
            found.append((int(m.group(1)), p))
    return found


def current_schema_version(conn: sqlite3.Connection) -> int:
    """Return the highest applied migration version, or 0 if fresh."""
    try:
        row = conn.execute(
            "SELECT MAX(version) AS v FROM schema_version"
        ).fetchone()
        return int(row["v"] or 0)
    except sqlite3.OperationalError:
        # schema_version table doesn't exist yet
        return 0


def apply_migrations(conn: sqlite3.Connection) -> list[int]:
    """Apply any pending migrations. Return the list of versions applied."""
    applied: list[int] = []
    current = current_schema_version(conn)
    for version, path in list_migrations():
        if version <= current:
            continue
        sql = path.read_text()
        with transaction(conn):
            conn.executescript(sql)
        applied.append(version)
    return applied


def backup(db_path: Path, backup_dir: Path, tag: str = "") -> Path:
    """Copy the DB to backup_dir with a timestamp. Return the backup path."""
    if not db_path.exists():
        raise FileNotFoundError(f"No database at {db_path}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    suffix = f"__{tag}" if tag else ""
    out = backup_dir / f"finance__{stamp}{suffix}.sqlite"
    shutil.copy2(db_path, out)
    return out
