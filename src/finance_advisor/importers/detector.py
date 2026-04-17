"""Format auto-detection for statement files.

Given a file path, return one of `csv`, `ofx`, `qfx`. Used when the user
doesn't pass `--format` explicitly.

Detection heuristic:
  1. Filename extension (`.csv`, `.ofx`, `.qfx`) wins — most files are honestly named.
  2. Fall back to content sniff: if the first 4KB contains `<OFX` or `<STMTTRN>`,
     treat as OFX. If it parses as CSV via csv.Sniffer, treat as CSV.
  3. Otherwise raise ValueError with what we saw.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path


def detect_format(path: Path) -> str:
    """Return `"csv"`, `"ofx"`, or `"qfx"`. Raises ValueError on unknown."""
    suffix = path.suffix.lower()
    if suffix in (".csv", ".tsv", ".txt"):
        return "csv"
    if suffix == ".ofx":
        return "ofx"
    if suffix == ".qfx":
        return "qfx"

    # Content sniff — read a small prefix.
    try:
        sample = path.read_text(encoding="utf-8", errors="replace")[:4096]
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc

    sample_upper = sample.upper()
    if "<OFX" in sample_upper or "<STMTTRN>" in sample_upper:
        # Can't distinguish OFX vs. QFX from content alone (they're identical
        # schema). Default to OFX; the parser handles both.
        return "ofx"

    try:
        csv.Sniffer().sniff(sample, delimiters=",\t;|")
        return "csv"
    except csv.Error:
        pass

    raise ValueError(
        f"{path.name}: could not detect format. Pass --format explicitly."
    )
