"""Normalization helpers shared by the import pipeline.

Nothing in here writes to the DB or reads from disk. Given raw strings from
a parser, these functions produce the deterministic forms that the database
and dedup logic depend on:

- `parse_date(s)` → ISO `YYYY-MM-DD` (or raises ValueError)
- `parse_amount(s)` → float (handles `$`, commas, parens for negatives, trailing `CR`/`DR`)
- `normalize_merchant(s)` → stable merchant string used for display and dedup
- `compute_dedup_key(...)` → sha256 hex of the canonical (account, date, amount, merchant) tuple

Stability is paramount: these must return the same output for the same input
across Python versions and runs. Any change to normalization is effectively a
schema change — it shifts every dedup_key and will create phantom duplicates
on re-import.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime


# ---------- dates ----------

_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%m/%d/%y",
    "%m-%d-%y",
    "%d/%m/%Y",
    "%d-%b-%Y",
    "%d-%b-%y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%Y%m%d",  # OFX style
)


def parse_date(value: str) -> str:
    """Parse a human or bank-formatted date → ISO `YYYY-MM-DD`.

    Raises ValueError if nothing matches. We try ISO first (cheap), then fall
    through a short list of common US bank formats. OFX dates (YYYYMMDD with
    optional HHMMSS) are handled by stripping trailing time.
    """
    if not value:
        raise ValueError("empty date")
    s = value.strip()

    # OFX datetime: take the leading 8 digits if present.
    if re.fullmatch(r"\d{8}.*", s):
        s = s[:8]

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"unrecognized date format: {value!r}")


# ---------- amounts ----------

_AMOUNT_CLEAN_RE = re.compile(r"[,$\s]")
_PAREN_RE = re.compile(r"^\((.+)\)$")
_TRAILING_CR_DR_RE = re.compile(r"^(.*?)\s*(CR|DR)$", re.IGNORECASE)


def parse_amount(value: str) -> float:
    """Parse a dollar amount → float.

    Handles: `$1,234.56`, `1234.56`, `(1,234.56)` (parens = negative),
    `1234.56 CR` (credit), `1234.56 DR` (debit → negative), leading `-`.
    Returns float. Raises ValueError on garbage.
    """
    if value is None:
        raise ValueError("empty amount")
    s = str(value).strip()
    if not s:
        raise ValueError("empty amount")

    sign = 1
    m = _PAREN_RE.match(s)
    if m:
        sign = -1
        s = m.group(1)

    m = _TRAILING_CR_DR_RE.match(s)
    if m:
        s, marker = m.group(1), m.group(2).upper()
        if marker == "DR":
            sign = -sign

    s = _AMOUNT_CLEAN_RE.sub("", s)

    try:
        return sign * float(s)
    except ValueError as exc:
        raise ValueError(f"unrecognized amount: {value!r}") from exc


# ---------- merchant normalization ----------

# Patterns we strip so that "AMZN MKTP US*1A2B3 AMZN.COM/BILL" and
# "Amazon.com AMZN*XYZ" collapse to the same root. This list is intentionally
# conservative: stripping too much causes false-positive merges.
_MERCHANT_STRIP_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\s+#\s*\d{2,}"),                # " #1234"
    re.compile(r"\s+\*[A-Z0-9]+"),               # " *XYZ123" (common CC suffix)
    re.compile(r"\s+POS\b", re.IGNORECASE),
    re.compile(r"\s+DEBIT\b", re.IGNORECASE),
    re.compile(r"\s+PURCHASE\b", re.IGNORECASE),
    re.compile(r"\s+PAYMENT\b", re.IGNORECASE),
    re.compile(r"\s+\d{10,}$"),                  # trailing long numbers
    re.compile(r"\s+[A-Z]{2}\s*$"),              # trailing state code
)

_MULTISPACE_RE = re.compile(r"\s+")


def normalize_merchant(raw: str) -> str:
    """Collapse a raw transaction description to a stable merchant string.

    Intentionally conservative — we strip obvious noise (POS flags, store
    numbers, trailing reference IDs) but keep the recognizable name intact.
    Returns the cleaned string uppercased (case-insensitive dedup target).

    Examples:
      "AMZN MKTP US*1A2B3C"        -> "AMZN MKTP US"
      "WHOLEFDS WC #10230"          -> "WHOLEFDS WC"
      "Amazon.com     AMZN*ABC123"  -> "AMAZON.COM AMZN"
    """
    if raw is None:
        return ""
    s = str(raw).strip()
    for pat in _MERCHANT_STRIP_PATTERNS:
        s = pat.sub("", s)
    s = _MULTISPACE_RE.sub(" ", s).strip()
    return s.upper()


# ---------- dedup key ----------

def compute_dedup_key(
    account_id: int,
    iso_date: str,
    amount: float,
    normalized_description: str,
) -> str:
    """sha256 hex digest of the canonical tuple.

    The amount is formatted to 2 decimals so that `100` and `100.00` collapse.
    The normalized description is already uppercased by `normalize_merchant`.
    """
    canonical = f"{account_id}|{iso_date}|{amount:.2f}|{normalized_description}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------- convenience ----------

def today_iso() -> str:
    """Today as ISO — factored out to make tests stubbable."""
    return date.today().isoformat()
