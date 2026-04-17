"""Statement importers — parse raw bank files into ParsedRow objects.

All parsers return a list of `ParsedRow` (see `base.py`). The importers here
do NO database work, NO normalization of merchants, and NO dedup — just
pure string-to-struct parsing.

The import command in `commands/import_.py` feeds these rows through
`normalize` and writes them to the DB.
"""

from __future__ import annotations

from finance_advisor.importers.base import ParsedRow, ParseError
from finance_advisor.importers.csv_importer import parse_csv
from finance_advisor.importers.ofx_importer import parse_ofx
from finance_advisor.importers.detector import detect_format

__all__ = [
    "ParsedRow",
    "ParseError",
    "parse_csv",
    "parse_ofx",
    "detect_format",
]
