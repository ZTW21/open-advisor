"""Unit tests for `finance_advisor.analytics`.

These are pure-function tests for the windowing helpers. The DB-touching
helpers are exercised in test_cashflow.py, test_anomalies.py, and
test_report_daily_weekly.py.
"""

from __future__ import annotations

from datetime import date

import pytest

from finance_advisor.analytics import (
    format_iso_week,
    parse_iso_week,
    parse_month,
    parse_window,
)


# ---------- parse_window ----------

def test_parse_window_days() -> None:
    start, end = parse_window("7d", today=date(2026, 4, 17))
    assert end == date(2026, 4, 17)
    # inclusive window of 7 days ending on the 17th → starts on the 11th
    assert start == date(2026, 4, 11)


def test_parse_window_thirty_days() -> None:
    start, end = parse_window("30d", today=date(2026, 4, 17))
    assert (end - start).days == 29  # 30 inclusive


def test_parse_window_months() -> None:
    start, end = parse_window("3m", today=date(2026, 4, 17))
    assert end == date(2026, 4, 17)
    # Roughly 3 months back.
    assert start == date(2026, 1, 18)


def test_parse_window_years() -> None:
    start, end = parse_window("1y", today=date(2026, 4, 17))
    assert end == date(2026, 4, 17)
    assert start == date(2025, 4, 18)


@pytest.mark.parametrize("bad", ["", "abc", "30", "30x", "-5d"])
def test_parse_window_rejects_garbage(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_window(bad)


# ---------- parse_month ----------

def test_parse_month_normal() -> None:
    start, end = parse_month("2026-03")
    assert start == date(2026, 3, 1)
    assert end == date(2026, 3, 31)


def test_parse_month_february_nonleap() -> None:
    start, end = parse_month("2025-02")
    assert end == date(2025, 2, 28)


def test_parse_month_february_leap() -> None:
    start, end = parse_month("2024-02")
    assert end == date(2024, 2, 29)


@pytest.mark.parametrize("bad", ["", "2026", "2026-13", "26-03", "March 2026"])
def test_parse_month_rejects_garbage(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_month(bad)


# ---------- ISO week round-trip ----------

def test_parse_and_format_iso_week_round_trip() -> None:
    start, end = parse_iso_week("2026-w15")
    # 2026-W15 starts Monday, Apr 6 2026.
    assert start == date(2026, 4, 6)
    assert end == date(2026, 4, 12)
    assert format_iso_week(start) == "2026-w15"


def test_parse_iso_week_w01_can_cross_year() -> None:
    # ISO 2024-W01 starts Mon 1 Jan 2024 (first week containing Thursday).
    start, end = parse_iso_week("2024-w01")
    assert start == date(2024, 1, 1)
    assert end == date(2024, 1, 7)


@pytest.mark.parametrize("bad", ["", "2026", "2026-15", "2026-W53-1"])
def test_parse_iso_week_rejects_garbage(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_iso_week(bad)
