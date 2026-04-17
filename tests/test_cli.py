"""Smoke tests for the CLI surface: does every command parse its args?"""

from __future__ import annotations

import json

from click.testing import CliRunner

from finance_advisor.cli import cli


def test_version(runner: CliRunner) -> None:
    """`finance --version` works without a DB."""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "finance" in result.output.lower()


def test_help(runner: CliRunner) -> None:
    """`finance --help` lists the subcommands."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for cmd in ("init", "account", "balance", "net-worth", "cashflow",
                "anomalies", "report", "import", "categorize", "reconcile",
                "rebalance", "export", "backup"):
        assert cmd in result.output


def test_stub_commands_return_not_yet_implemented(invoke) -> None:
    """Stubbed commands return a standard not_yet_implemented payload.

    As phases land, items graduate out of this list: `report monthly` became
    real in Phase 7; `rebalance` became real in Phase 9; `report quarterly`
    and `report annual` became real in Phase 10. Reconcile is still a stub.
    """
    invoke("init")
    for args in (
        ("reconcile", "--account", "x", "--balance", "0", "--as-of", "2026-01-01"),
    ):
        result = invoke(*args)
        # Stubs exit 0 but payload.ok == False. Some commands may exit
        # non-zero depending on click; we just care the payload is parseable.
        payload = json.loads(result.output)
        assert payload["ok"] is False
        assert payload["error"] == "not_yet_implemented"


def test_help_lists_phase10_commands(runner: CliRunner) -> None:
    """Phase 10 commands show up in `finance --help`."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "fees" in result.output
    assert "tax-pack" in result.output


def test_help_lists_phase11_commands(runner: CliRunner) -> None:
    """Phase 11 commands show up in `finance --help`."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "mode" in result.output
    assert "automation" in result.output
