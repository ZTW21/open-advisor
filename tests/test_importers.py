"""Tests for `finance_advisor.importers` (CSV + OFX parsing).

These exercise the parsers directly — no DB, no CLI. We verify:
  - Sign convention (positive = inflow to account)
  - Debit/Credit column handling
  - Header detection with skipped preamble rows
  - OFX SGML and XML tag extraction
  - Format auto-detection
"""

from __future__ import annotations

from pathlib import Path

import pytest

from finance_advisor.importers import (
    ParseError,
    detect_format,
    parse_csv,
    parse_ofx,
)


# ---------- CSV ----------

def _write(p: Path, content: str) -> Path:
    p.write_text(content)
    return p


def test_csv_single_amount_column(tmp_path: Path) -> None:
    """A simple CSV with one signed Amount column parses correctly."""
    csv_text = (
        "Date,Description,Amount\n"
        "01/03/2026,WHOLE FOODS,-87.45\n"
        "01/15/2026,PAYROLL DEPOSIT,3200.00\n"
    )
    p = _write(tmp_path / "simple.csv", csv_text)
    rows = parse_csv(p)
    assert len(rows) == 2
    assert rows[0].amount == pytest.approx(-87.45)
    assert rows[1].amount == pytest.approx(3200.00)
    assert rows[0].description == "WHOLE FOODS"


def test_csv_debit_credit_columns(tmp_path: Path) -> None:
    """Debit/Credit columns: only one populated per row; sign is enforced."""
    csv_text = (
        "Date,Description,Debit,Credit\n"
        "01/03/2026,WHOLE FOODS,87.45,\n"
        "01/15/2026,PAYROLL DEPOSIT,,3200.00\n"
    )
    p = _write(tmp_path / "dc.csv", csv_text)
    rows = parse_csv(p)
    assert len(rows) == 2
    # Debit → outflow → negative
    assert rows[0].amount == pytest.approx(-87.45)
    # Credit → inflow → positive
    assert rows[1].amount == pytest.approx(3200.00)


def test_csv_preamble_before_header(tmp_path: Path) -> None:
    """Leading junk rows before the real header are skipped."""
    csv_text = (
        "Account: Chase Checking\n"
        "Statement period: 2026-01-01 to 2026-01-31\n"
        "\n"
        "Date,Description,Amount\n"
        "01/03/2026,WHOLE FOODS,-87.45\n"
    )
    p = _write(tmp_path / "preamble.csv", csv_text)
    rows = parse_csv(p)
    assert len(rows) == 1
    assert rows[0].description == "WHOLE FOODS"


def test_csv_extra_columns_are_ignored(tmp_path: Path) -> None:
    """Columns beyond date/desc/amount don't confuse the parser."""
    csv_text = (
        "Transaction Date,Post Date,Description,Category,Type,Amount\n"
        "01/03/2026,01/04/2026,WHOLE FOODS MKT,Groceries,Sale,-87.45\n"
    )
    p = _write(tmp_path / "extra.csv", csv_text)
    rows = parse_csv(p)
    assert len(rows) == 1
    assert rows[0].amount == pytest.approx(-87.45)


def test_csv_rejects_missing_required_columns(tmp_path: Path) -> None:
    """Header row without a date column is a ParseError."""
    csv_text = "Foo,Bar,Baz\n1,2,3\n"
    p = _write(tmp_path / "bad.csv", csv_text)
    with pytest.raises(ParseError):
        parse_csv(p)


def test_csv_rejects_bad_amount(tmp_path: Path) -> None:
    """Amount that won't parse surfaces with a line number."""
    csv_text = (
        "Date,Description,Amount\n"
        "01/03/2026,WHOLE FOODS,not-a-number\n"
    )
    p = _write(tmp_path / "bad_amt.csv", csv_text)
    with pytest.raises(ParseError, match="line"):
        parse_csv(p)


def test_csv_empty_file_raises(tmp_path: Path) -> None:
    p = _write(tmp_path / "empty.csv", "")
    with pytest.raises(ParseError):
        parse_csv(p)


# ---------- OFX ----------

_OFX_MINIMAL = """<?xml version="1.0"?>
<?OFX OFXHEADER="200" VERSION="200"?>
<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT</TRNTYPE>
<DTPOSTED>20260310120000</DTPOSTED>
<TRNAMT>-42.50</TRNAMT>
<FITID>ID00001</FITID>
<NAME>UBER EATS</NAME>
<MEMO>Dinner Tuesday</MEMO>
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT</TRNTYPE>
<DTPOSTED>20260315000000</DTPOSTED>
<TRNAMT>25.00</TRNAMT>
<FITID>ID00002</FITID>
<NAME>VENMO CASHOUT</NAME>
</STMTTRN>
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>
"""


def test_ofx_parses_two_transactions(tmp_path: Path) -> None:
    p = _write(tmp_path / "sample.ofx", _OFX_MINIMAL)
    rows = parse_ofx(p)
    assert len(rows) == 2
    assert rows[0].amount == pytest.approx(-42.50)
    assert "UBER EATS" in rows[0].description.upper()
    # NAME + MEMO concatenated when both present.
    assert "DINNER TUESDAY" in rows[0].description.upper()
    assert rows[0].posted_id == "ID00001"


def test_ofx_date_parseable_from_ofx_datetime(tmp_path: Path) -> None:
    """OFX DTPOSTED is YYYYMMDDHHMMSS — we store the raw string but it must parse."""
    from finance_advisor.normalize import parse_date

    p = _write(tmp_path / "ofx.ofx", _OFX_MINIMAL)
    rows = parse_ofx(p)
    assert parse_date(rows[0].date_raw) == "2026-03-10"


def test_ofx_empty_file_raises(tmp_path: Path) -> None:
    p = _write(tmp_path / "empty.ofx", "<?xml version='1.0'?><OFX></OFX>")
    with pytest.raises(ParseError, match="STMTTRN"):
        parse_ofx(p)


# ---------- format detection ----------

def test_detect_format_by_extension(tmp_path: Path) -> None:
    csv_p = _write(tmp_path / "a.csv", "Date,Description,Amount\n2026-01-01,X,1\n")
    ofx_p = _write(tmp_path / "a.ofx", _OFX_MINIMAL)
    qfx_p = _write(tmp_path / "a.qfx", _OFX_MINIMAL)
    assert detect_format(csv_p) == "csv"
    assert detect_format(ofx_p) == "ofx"
    assert detect_format(qfx_p) == "qfx"


def test_detect_format_by_content_when_extension_missing(tmp_path: Path) -> None:
    """A file named without a helpful suffix still detects by content."""
    ofx_p = _write(tmp_path / "statement", _OFX_MINIMAL)
    assert detect_format(ofx_p) == "ofx"
