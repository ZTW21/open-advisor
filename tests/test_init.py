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


# ---------------------------------------------------------------------------
# Template hydration
#
# `finance init` copies every file in `<finance_dir>/templates/` into the
# corresponding path in the finance directory, skipping files that already
# exist. This is what lets `git pull upstream main` land safely without
# clobbering a user's populated STRATEGY.md, memory/, state/, etc.
# ---------------------------------------------------------------------------


def test_init_without_templates_dir_is_noop(invoke) -> None:
    """No templates/ dir — init still succeeds; hydration lists are empty."""
    result = invoke("init")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["templates_hydrated"] == []
    assert payload["templates_skipped"] == []


def test_init_hydrates_root_templates(invoke, finance_dir: Path) -> None:
    """Files in templates/ at the root copy to the corresponding finance_dir path."""
    templates = finance_dir / "templates"
    templates.mkdir()
    (templates / "STRATEGY.md").write_text("# Strategy template\n")
    (templates / "goals.md").write_text("# Goals template\n")

    result = invoke("init")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)

    assert set(payload["templates_hydrated"]) == {"STRATEGY.md", "goals.md"}
    assert payload["templates_skipped"] == []
    assert (finance_dir / "STRATEGY.md").read_text() == "# Strategy template\n"
    assert (finance_dir / "goals.md").read_text() == "# Goals template\n"


def test_init_hydrates_nested_templates(invoke, finance_dir: Path) -> None:
    """Nested paths in templates/ (e.g., state/, memory/) are preserved."""
    templates = finance_dir / "templates"
    (templates / "state").mkdir(parents=True)
    (templates / "memory").mkdir(parents=True)
    (templates / "state" / "net-worth.md").write_text("# net worth\n")
    (templates / "memory" / "MEMORY.md").write_text("# memory index\n")

    result = invoke("init")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)

    assert set(payload["templates_hydrated"]) == {
        # os-native separator is fine because these are pathlib.relative_to strings
        str(Path("memory") / "MEMORY.md"),
        str(Path("state") / "net-worth.md"),
    }
    assert (finance_dir / "state" / "net-worth.md").read_text() == "# net worth\n"
    assert (finance_dir / "memory" / "MEMORY.md").read_text() == "# memory index\n"


def test_init_does_not_overwrite_existing_files(invoke, finance_dir: Path) -> None:
    """Hydration is non-destructive — existing files are never overwritten."""
    templates = finance_dir / "templates"
    templates.mkdir()
    (templates / "STRATEGY.md").write_text("# Template content — should NOT win\n")

    # User has already populated STRATEGY.md.
    (finance_dir / "STRATEGY.md").write_text("# USER CONTENT — preserve me\n")

    result = invoke("init")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)

    assert payload["templates_hydrated"] == []
    assert payload["templates_skipped"] == ["STRATEGY.md"]
    assert (finance_dir / "STRATEGY.md").read_text() == "# USER CONTENT — preserve me\n"


def test_init_is_idempotent_on_hydration(invoke, finance_dir: Path) -> None:
    """Running init twice hydrates once, then reports everything as skipped."""
    templates = finance_dir / "templates"
    templates.mkdir()
    (templates / "goals.md").write_text("# goals\n")

    first = invoke("init")
    first_payload = json.loads(first.output)
    assert first_payload["templates_hydrated"] == ["goals.md"]
    assert first_payload["templates_skipped"] == []

    second = invoke("init")
    second_payload = json.loads(second.output)
    assert second_payload["templates_hydrated"] == []
    assert second_payload["templates_skipped"] == ["goals.md"]


def test_init_picks_up_new_templates_after_upgrade(invoke, finance_dir: Path) -> None:
    """After a `git pull` adds a new template, re-running init hydrates it."""
    templates = finance_dir / "templates"
    templates.mkdir()
    (templates / "goals.md").write_text("# goals\n")

    # First release hydrates goals.md.
    invoke("init")
    assert (finance_dir / "goals.md").exists()

    # Simulate an upstream upgrade that added a new template.
    (templates / "principles.md").write_text("# principles — new in v1.1\n")

    # Re-running init picks it up without touching existing files.
    result = invoke("init")
    payload = json.loads(result.output)
    assert payload["templates_hydrated"] == ["principles.md"]
    assert "goals.md" in payload["templates_skipped"]
    assert (finance_dir / "principles.md").read_text() == "# principles — new in v1.1\n"


def test_init_preserves_file_content_byte_for_byte(invoke, finance_dir: Path) -> None:
    """Template content must copy verbatim — no trailing-newline fiddling, no re-encoding."""
    templates = finance_dir / "templates"
    templates.mkdir()
    raw = "---\nname: test\nupdated: 2026-04-17\n---\n\n# Body\n\nSpecial chars: — ✓ ✗\n"
    (templates / "profile.md").write_text(raw, encoding="utf-8")

    result = invoke("init")
    assert result.exit_code == 0, result.output

    copied = (finance_dir / "profile.md").read_text(encoding="utf-8")
    assert copied == raw
