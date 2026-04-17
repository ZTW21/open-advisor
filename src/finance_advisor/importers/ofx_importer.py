"""OFX/QFX statement parser.

OFX comes in two flavors:
  - OFX 1.x: SGML (looks like XML but not strictly well-formed — tags often
    don't have explicit closers).
  - OFX 2.x: XML-ish, with a custom `?OFX` processing instruction header.

We implement a pragmatic parser that extracts <STMTTRN> records using regex.
This is intentional — bringing in `ofxtools` would add an install-time
dependency, and real-world OFX files from banks are messy enough that even
`ofxtools` struggles without format hints.

What we extract from each STMTTRN:
  - DTPOSTED → date (first 8 digits, YYYYMMDD)
  - TRNAMT   → amount
  - NAME / MEMO / PAYEE → description (concat in that priority)
  - FITID    → posted_id

Anything we can't make sense of raises ParseError.
"""

from __future__ import annotations

import re
from pathlib import Path

from finance_advisor.importers.base import ParsedRow, ParseError
from finance_advisor.normalize import parse_amount, parse_date


# Matches one <STMTTRN>...</STMTTRN> block. DOTALL so newlines inside count.
_STMTTRN_RE = re.compile(r"<STMTTRN>(.*?)</STMTTRN>", re.DOTALL | re.IGNORECASE)

# SGML-style tag: <TAG>value (value runs until next tag or end of line).
# XML-style tag: <TAG>value</TAG>.
# Both forms exist in the wild; the pattern below captures either.
def _extract_field(block: str, tag: str) -> str | None:
    tag_upper = tag.upper()
    # Try XML form first: <TAG>value</TAG>
    m = re.search(
        rf"<{tag_upper}>(.*?)</{tag_upper}>",
        block,
        re.DOTALL | re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    # SGML form: <TAG>value_up_to_next_tag_or_newline
    m = re.search(rf"<{tag_upper}>([^<\r\n]*)", block, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def parse_ofx(path: Path) -> list[ParsedRow]:
    """Parse an OFX/QFX file → list of ParsedRow."""
    # OFX files are typically latin-1 or cp1252 in the 1.x era; modern ones
    # are utf-8. Use utf-8 with error replacement to avoid breaking on stray
    # bytes in older exports.
    text = path.read_text(encoding="utf-8", errors="replace")

    blocks = _STMTTRN_RE.findall(text)
    if not blocks:
        raise ParseError(
            f"{path.name}: no <STMTTRN> records found — is this really OFX/QFX?"
        )

    rows: list[ParsedRow] = []
    for i, block in enumerate(blocks, start=1):
        dt = _extract_field(block, "DTPOSTED")
        amt = _extract_field(block, "TRNAMT")

        name = _extract_field(block, "NAME") or ""
        memo = _extract_field(block, "MEMO") or ""
        payee = _extract_field(block, "PAYEE") or ""
        # Prefer NAME, then PAYEE, then MEMO. Concat memo if it adds info.
        description = name or payee or memo
        if memo and memo not in description:
            description = f"{description} {memo}".strip()

        fitid = _extract_field(block, "FITID")

        if not dt or amt is None:
            raise ParseError(
                f"{path.name}: STMTTRN #{i} missing DTPOSTED or TRNAMT — block was {block!r}"
            )

        try:
            amount = parse_amount(amt)
            parse_date(dt)  # validation only; store raw for transparency
        except ValueError as exc:
            raise ParseError(f"{path.name} STMTTRN #{i}: {exc}") from exc

        rows.append(
            ParsedRow(
                source_line=i,  # block index, since OFX doesn't have real line semantics
                date_raw=dt,
                amount=amount,
                description=description,
                posted_id=fitid,
            )
        )

    return rows
