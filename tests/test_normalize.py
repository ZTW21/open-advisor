"""Tests for `finance_advisor.normalize`.

These are pure-function tests — no DB, no file I/O. The normalization layer
is the foundation of dedup, so stability here matters more than any single
CLI feature.
"""

from __future__ import annotations

import pytest

from finance_advisor.normalize import (
    compute_dedup_key,
    normalize_merchant,
    parse_amount,
    parse_date,
)


# ---------- dates ----------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2026-04-17", "2026-04-17"),
        ("2026/04/17", "2026-04-17"),
        ("04/17/2026", "2026-04-17"),
        ("04-17-2026", "2026-04-17"),
        ("4/17/2026", "2026-04-17"),
        ("4/17/26", "2026-04-17"),
        ("17-Apr-2026", "2026-04-17"),
        ("Apr 17, 2026", "2026-04-17"),
        ("April 17, 2026", "2026-04-17"),
        ("20260417", "2026-04-17"),
        ("20260417120000", "2026-04-17"),  # OFX datetime
    ],
)
def test_parse_date_accepted_formats(raw: str, expected: str) -> None:
    assert parse_date(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "not-a-date", "2026-13-01", "13/45/2026"])
def test_parse_date_rejects_garbage(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_date(raw)


# ---------- amounts ----------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("100", 100.0),
        ("100.00", 100.00),
        ("1,234.56", 1234.56),
        ("$1,234.56", 1234.56),
        ("-42.50", -42.50),
        ("(42.50)", -42.50),
        ("(1,234.56)", -1234.56),
        ("42.50 CR", 42.50),
        ("42.50 DR", -42.50),
        ("  42.50  ", 42.50),
    ],
)
def test_parse_amount(raw: str, expected: float) -> None:
    assert parse_amount(raw) == pytest.approx(expected)


@pytest.mark.parametrize("raw", ["", "   ", "abc", "$$"])
def test_parse_amount_rejects_garbage(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_amount(raw)


# ---------- merchant normalization ----------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("WHOLE FOODS MKT #10230 NYC", "WHOLE FOODS MKT"),
        ("WHOLEFDS WC #10230", "WHOLEFDS WC"),
        ("AMZN MKTP US*1A2B3C", "AMZN MKTP US"),
        ("STARBUCKS STORE #1234 NYC", "STARBUCKS STORE"),
        ("Amazon.com", "AMAZON.COM"),
        ("   multiple   spaces   ", "MULTIPLE SPACES"),
        ("", ""),
    ],
)
def test_normalize_merchant(raw: str, expected: str) -> None:
    assert normalize_merchant(raw) == expected


def test_normalize_merchant_is_idempotent() -> None:
    """Normalizing an already-normalized merchant changes nothing."""
    once = normalize_merchant("WHOLE FOODS MKT #10230 NYC")
    twice = normalize_merchant(once)
    assert once == twice


# ---------- dedup key ----------

def test_dedup_key_is_deterministic() -> None:
    """Same inputs → same hex digest. This is the whole point."""
    k1 = compute_dedup_key(1, "2026-04-01", -87.45, "WHOLE FOODS MKT")
    k2 = compute_dedup_key(1, "2026-04-01", -87.45, "WHOLE FOODS MKT")
    assert k1 == k2
    assert len(k1) == 64  # sha256 hex length


def test_dedup_key_distinguishes_account() -> None:
    k1 = compute_dedup_key(1, "2026-04-01", -87.45, "WHOLE FOODS")
    k2 = compute_dedup_key(2, "2026-04-01", -87.45, "WHOLE FOODS")
    assert k1 != k2


def test_dedup_key_rounds_amount_to_cents() -> None:
    """100 and 100.00 should hash the same — float representations shouldn't split them."""
    k1 = compute_dedup_key(1, "2026-04-01", 100, "PAYROLL")
    k2 = compute_dedup_key(1, "2026-04-01", 100.00, "PAYROLL")
    assert k1 == k2


def test_dedup_key_distinguishes_merchants() -> None:
    k1 = compute_dedup_key(1, "2026-04-01", -10.00, "STARBUCKS")
    k2 = compute_dedup_key(1, "2026-04-01", -10.00, "PEETS COFFEE")
    assert k1 != k2
