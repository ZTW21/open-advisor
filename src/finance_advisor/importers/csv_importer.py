"""Generic CSV statement parser.

Bank CSV formats vary wildly. Rather than maintain a format-per-bank codepath,
we detect the header row's column purposes and work from there. Common cases
handled:

  - `Date, Description, Amount` (single signed amount column)
  - `Date, Description, Debit, Credit` (two columns; at most one populated)
  - `Transaction Date, Post Date, Description, Amount, ...` (extra columns ignored)
  - `Date, Payee, Amount, Type, Balance` (QFX-style export)

Ambiguity strategy: if we can't identify a column with confidence, we raise
`ParseError` with a message that tells the user what we saw — better to fail
loudly than to silently mis-map columns.

Sign convention: we emit positive = inflow, negative = outflow. Many banks'
CSVs use the opposite convention (debit column positive = outflow). The
importer resolves this by column purpose, not by guessing from the number.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Optional

from finance_advisor.importers.base import ParsedRow, ParseError
from finance_advisor.normalize import parse_amount, parse_date


# Header name fragments that identify each role. Case-insensitive substring
# match. First hit wins; order matters — put specific before general.
_DATE_HEADERS = (
    "transaction date",
    "post date",
    "posted date",
    "posting date",
    "date",
)
_DESCRIPTION_HEADERS = (
    "description",
    "payee",
    "merchant",
    "name",
    "memo",
    "details",
    "narrative",
)
_AMOUNT_HEADERS = (
    "amount",
    "transaction amount",
)
_DEBIT_HEADERS = ("debit", "withdrawal", "withdrawals", "money out")
_CREDIT_HEADERS = ("credit", "deposit", "deposits", "money in")


def _find_col(headers: list[str], candidates: tuple[str, ...]) -> Optional[int]:
    """Return the index of the first header that contains any candidate string."""
    lowered = [h.strip().lower() for h in headers]
    for cand in candidates:
        for i, h in enumerate(lowered):
            if cand in h:
                return i
    return None


def _read_non_empty_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip()]


def _find_header_row(lines: list[str]) -> int:
    """Scan the first several lines for a header row.

    Many bank CSVs have a leading "Account summary" block before the real
    transaction table. We look for the first row that mentions a date-ish
    column; if none is found in the first 20 rows we raise.
    """
    for i, line in enumerate(lines[:20]):
        fields = [f.strip().lower() for f in next(csv.reader(io.StringIO(line)))]
        if any(h in f for h in _DATE_HEADERS for f in fields):
            if any(h in f for h in _DESCRIPTION_HEADERS for f in fields):
                return i
    raise ParseError(
        "could not locate a header row with date+description columns in the first 20 lines"
    )


def parse_csv(path: Path) -> list[ParsedRow]:
    """Parse a CSV file → list of ParsedRow. Raises ParseError on malformed files."""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = _read_non_empty_lines(text)
    if not lines:
        raise ParseError(f"{path.name} is empty")

    header_row_idx = _find_header_row(lines)
    body = "\n".join(lines[header_row_idx:])

    reader = csv.reader(io.StringIO(body))
    try:
        headers = next(reader)
    except StopIteration as exc:
        raise ParseError(f"{path.name} has no data rows after the header") from exc

    date_col = _find_col(headers, _DATE_HEADERS)
    desc_col = _find_col(headers, _DESCRIPTION_HEADERS)
    amount_col = _find_col(headers, _AMOUNT_HEADERS)
    debit_col = _find_col(headers, _DEBIT_HEADERS)
    credit_col = _find_col(headers, _CREDIT_HEADERS)

    if date_col is None or desc_col is None:
        raise ParseError(
            f"{path.name}: could not identify date and description columns. "
            f"Headers seen: {headers!r}"
        )
    if amount_col is None and (debit_col is None or credit_col is None):
        raise ParseError(
            f"{path.name}: need either one 'Amount' column or both 'Debit' and "
            f"'Credit' columns. Headers seen: {headers!r}"
        )

    rows: list[ParsedRow] = []
    # Line numbering: header row's real line number + 1 for the first data row.
    # `header_row_idx` is index into the non-empty-lines list; we use that as a
    # rough proxy for source_line. Good enough for error messages.
    for offset, record in enumerate(reader, start=1):
        if not any(c.strip() for c in record):
            continue
        source_line = header_row_idx + 1 + offset
        try:
            raw_date = record[date_col].strip()
            description = record[desc_col].strip()

            if amount_col is not None:
                amount = parse_amount(record[amount_col])
            else:
                # Debit/Credit columns. At most one populated.
                debit_val = record[debit_col].strip() if debit_col is not None else ""
                credit_val = record[credit_col].strip() if credit_col is not None else ""
                if debit_val and credit_val:
                    raise ParseError(
                        f"line {source_line}: both debit and credit columns populated"
                    )
                if credit_val:
                    amount = parse_amount(credit_val)  # inflow = positive
                elif debit_val:
                    amount = -abs(parse_amount(debit_val))  # outflow = negative
                else:
                    # Empty row — skip silently.
                    continue

            # Validate the date parses; we pass through the raw string so
            # downstream callers can see what the file actually said.
            parse_date(raw_date)

            rows.append(
                ParsedRow(
                    source_line=source_line,
                    date_raw=raw_date,
                    amount=amount,
                    description=description,
                    posted_id=None,
                )
            )
        except ValueError as exc:
            raise ParseError(f"{path.name} line {source_line}: {exc}") from exc
        except IndexError as exc:
            raise ParseError(
                f"{path.name} line {source_line}: row has fewer columns than the header"
            ) from exc

    return rows
