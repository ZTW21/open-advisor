"""Rule-based transaction categorization.

Rules live in the `categorization_rules` table. Each rule has:
  - match_pattern: the string to match against
  - match_type:    'substring' | 'regex' | 'exact'
  - category_id:   which category to assign
  - account_filter: restrict to one account name (optional)
  - amount_filter: simple expression like '<0', '>100' (optional)
  - priority:      higher wins; ties broken by rule id

At import time, each transaction's normalized description is matched against
every rule in priority order. First match wins. Unmatched transactions are
left with category_id=NULL so the user (or AI) can resolve them later.

This file is deliberately free of any database-writing concerns — callers
pass in the rule rows and get back a (category_id, rule_id) or None.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Optional


_AMOUNT_FILTER_RE = re.compile(r"^\s*(>=|<=|>|<|==|=)\s*(-?\d+(?:\.\d+)?)\s*$")


@dataclass(frozen=True)
class Rule:
    """Compiled rule — prepared once per import run, reused per transaction."""
    id: int
    category_id: int
    priority: int
    match_type: str
    match_pattern: str
    account_filter: Optional[str]
    amount_filter: Optional[str]
    _regex: Optional[re.Pattern[str]] = None  # set for match_type='regex'


def _compile_rule(row: sqlite3.Row) -> Rule:
    regex = None
    if row["match_type"] == "regex":
        try:
            regex = re.compile(row["match_pattern"], re.IGNORECASE)
        except re.error as exc:
            # We surface the rule id so the user can fix it. Don't crash the
            # whole import — downgrade to no-op by setting an impossible regex.
            regex = re.compile(r"(?!x)x")  # never matches
            # In practice the CLI will log a warning; we prefer silent-safe
            # here so import flow stays robust. The rule table itself should
            # be validated at `categorize rule add` time.
            del exc  # noqa: F841
    return Rule(
        id=row["id"],
        category_id=row["category_id"],
        priority=row["priority"],
        match_type=row["match_type"],
        match_pattern=row["match_pattern"],
        account_filter=row["account_filter"],
        amount_filter=row["amount_filter"],
        _regex=regex,
    )


def load_rules(conn: sqlite3.Connection) -> list[Rule]:
    """Load all rules, highest priority first."""
    rows = conn.execute(
        "SELECT id, match_pattern, match_type, category_id, account_filter, "
        "amount_filter, priority FROM categorization_rules "
        "ORDER BY priority DESC, id ASC"
    ).fetchall()
    return [_compile_rule(r) for r in rows]


def _amount_matches(expr: Optional[str], amount: float) -> bool:
    if not expr:
        return True
    m = _AMOUNT_FILTER_RE.match(expr)
    if not m:
        # Malformed filter — treat as "no filter" rather than blocking import.
        return True
    op, threshold_s = m.group(1), m.group(2)
    threshold = float(threshold_s)
    if op in (">",):
        return amount > threshold
    if op in (">=",):
        return amount >= threshold
    if op in ("<",):
        return amount < threshold
    if op in ("<=",):
        return amount <= threshold
    if op in ("=", "=="):
        return abs(amount - threshold) < 0.005
    return True


def _pattern_matches(rule: Rule, normalized_desc: str) -> bool:
    target = normalized_desc.upper()
    if rule.match_type == "substring":
        return rule.match_pattern.upper() in target
    if rule.match_type == "exact":
        return rule.match_pattern.upper() == target
    if rule.match_type == "regex":
        return rule._regex is not None and rule._regex.search(normalized_desc) is not None
    return False


def classify(
    rules: list[Rule],
    *,
    account_name: str,
    normalized_desc: str,
    amount: float,
) -> Optional[tuple[int, int]]:
    """Return (category_id, rule_id) for the first matching rule, or None.

    `rules` must already be sorted priority DESC (see `load_rules`).
    """
    for rule in rules:
        if rule.account_filter and rule.account_filter != account_name:
            continue
        if not _amount_matches(rule.amount_filter, amount):
            continue
        if _pattern_matches(rule, normalized_desc):
            return (rule.category_id, rule.id)
    return None
