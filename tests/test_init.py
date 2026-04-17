"""Tests for `finance init`."""

from __future__ import annotations

import json
from pathlib import Path


def test_init_creates_db(invoke, db_path: Path) -> None:
    """`finance init` should create the SQLite file and apply migrations."""
    assert not db_path.exists()
    result = invoke("init")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["created"] is True
    assert payload["schema_version"] >= 1
    assert db_path.exists()


def test_init_is_idempotent(invoke, db_path: Path) -> None:
    """Running init twice is safe; second run doesn't re-apply migrations."""
    first = invoke("init")
    assert first.exit_code == 0
    first_payload = json.loads(first.output)
    assert first_payload["created"] is True

    second = invoke("init")
    assert second.exit_code == 0
    second_payload = json.loads(second.output)
    assert second_payload["created"] is False
    assert second_payload["migrations_applied"] == []
    assert second_payload["schema_version"] == first_payload["schema_version"]
