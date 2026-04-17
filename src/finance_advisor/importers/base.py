"""Shared types for all importers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class ParseError(ValueError):
    """Raised when a parser cannot make sense of a file."""


@dataclass(frozen=True)
class ParsedRow:
    """One transaction as it came out of a parser — before normalization or dedup.

    Fields:
        source_line: 1-based index in the source file (for error messages).
        date_raw:    the date string exactly as it appeared.
        amount:      signed float (positive = inflow to account, negative = outflow).
                     Importer is responsible for translating bank sign conventions.
        description: the raw merchant/description string.
        posted_id:   bank-provided stable ID if available (OFX FITID, etc.)
                     — useful for stronger dedup, but not required.
    """
    source_line: int
    date_raw: str
    amount: float
    description: str
    posted_id: Optional[str] = None
