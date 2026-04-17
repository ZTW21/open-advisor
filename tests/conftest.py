"""Shared test fixtures.

Every test gets a fresh finance directory in a temp path with the migrations
applied. Use the `finance_dir` fixture to get the path; use the `cli_runner`
fixture to invoke commands with that directory's DB.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from finance_advisor.cli import cli
from finance_advisor.db import apply_migrations, connect


@pytest.fixture
def finance_dir(tmp_path: Path) -> Path:
    """A fresh finance directory with CLAUDE.md marker and data/ set up."""
    fd = tmp_path / "finance"
    fd.mkdir()
    (fd / "CLAUDE.md").write_text("# Finance dir marker\n")
    (fd / "data").mkdir()
    return fd


@pytest.fixture
def db_path(finance_dir: Path) -> Path:
    """Path where the DB will live (not yet created)."""
    return finance_dir / "data" / "finance.sqlite"


@pytest.fixture
def initialized_db(db_path: Path) -> Path:
    """A DB with migrations applied. Returns the path."""
    conn = connect(db_path)
    try:
        apply_migrations(conn)
    finally:
        conn.close()
    return db_path


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def invoke(runner: CliRunner, db_path: Path):
    """Return a callable that invokes the CLI with --db pointed at db_path."""

    def _invoke(*args: str, json_output: bool = True) -> object:
        base = ["--db", str(db_path)]
        if json_output:
            base.append("--json")
        return runner.invoke(cli, base + list(args), catch_exceptions=False)

    return _invoke
