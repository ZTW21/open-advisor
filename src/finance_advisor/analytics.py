"""Shared analytics helpers — windowing, aggregation, anomaly scoring.

These are pure functions that operate on sqlite3 connections and return plain
dicts. Commands (cashflow, anomalies, report daily/weekly) compose them.

Design notes:
  - All dates are ISO `YYYY-MM-DD` strings.
  - Windows are inclusive of both endpoints.
  - Functions never print; they return dicts. Printing happens in commands.
  - We never assume a month is 30 days — use `date` math explicitly.
"""

from __future__ import annotations

import calendar
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, Optional


# ---------- window parsing ----------

_WINDOW_RE = re.compile(r"^(\d+)\s*([dwmy])$", re.IGNORECASE)


def parse_window(spec: str, *, today: Optional[date] = None) -> tuple[date, date]:
    """Convert a window spec like '7d', '30d', '3m', '1y' to (start, end).

    End date is `today` (default = real today). Start is inclusive.
    """
    today = today or date.today()
    m = _WINDOW_RE.match(spec.strip())
    if not m:
        raise ValueError(f"Invalid window spec: {spec!r} (expected e.g. '7d', '30d', '3m', '1y')")
    n = int(m.group(1))
    unit = m.group(2).lower()
    if unit == "d":
        start = today - timedelta(days=n - 1)
    elif unit == "w":
        start = today - timedelta(weeks=n) + timedelta(days=1)
    elif unit == "m":
        # Month math: go back n months, clamped to valid day.
        year = today.year
        month = today.month - n
        while month <= 0:
            month += 12
            year -= 1
        day = min(today.day, calendar.monthrange(year, month)[1])
        start = date(year, month, day) + timedelta(days=1)
    elif unit == "y":
        try:
            start = date(today.year - n, today.month, today.day) + timedelta(days=1)
        except ValueError:
            # Feb 29 on non-leap
            start = date(today.year - n, today.month, 28) + timedelta(days=1)
    else:  # pragma: no cover — regex wouldn't match
        raise ValueError(f"Unknown window unit: {unit}")
    return start, today


def parse_month(spec: str) -> tuple[date, date]:
    """Convert 'YYYY-MM' to the first/last days of that month."""
    try:
        dt = datetime.strptime(spec, "%Y-%m").date()
    except ValueError as e:
        raise ValueError(f"Invalid month: {spec!r} (expected YYYY-MM)") from e
    last_day = calendar.monthrange(dt.year, dt.month)[1]
    return date(dt.year, dt.month, 1), date(dt.year, dt.month, last_day)


_QUARTER_RE = re.compile(r"^(\d{4})-[Qq]([1-4])$")


def parse_quarter(spec: str) -> tuple[date, date]:
    """Convert 'YYYY-Qn' (n in 1..4) to (first day of quarter, last day of quarter)."""
    m = _QUARTER_RE.match(spec.strip())
    if not m:
        raise ValueError(f"Invalid quarter: {spec!r} (expected YYYY-Qn, n=1..4)")
    year = int(m.group(1))
    q = int(m.group(2))
    start_month = 3 * (q - 1) + 1
    end_month = start_month + 2
    last_day = calendar.monthrange(year, end_month)[1]
    return date(year, start_month, 1), date(year, end_month, last_day)


def format_quarter(d: date) -> str:
    """Format a date as the quarter it falls in: 'YYYY-Qn'."""
    q = (d.month - 1) // 3 + 1
    return f"{d.year:04d}-Q{q}"


def prior_quarter(spec: str) -> str:
    """Given 'YYYY-Qn', return 'YYYY-Qn' of the preceding quarter."""
    m = _QUARTER_RE.match(spec.strip())
    if not m:
        raise ValueError(f"Invalid quarter: {spec!r}")
    year = int(m.group(1))
    q = int(m.group(2))
    if q == 1:
        return f"{year - 1:04d}-Q4"
    return f"{year:04d}-Q{q - 1}"


def parse_year(spec: str) -> tuple[date, date]:
    """Convert 'YYYY' to (Jan 1, Dec 31)."""
    try:
        year = int(spec.strip())
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid year: {spec!r} (expected YYYY)") from e
    if year < 1900 or year > 2999:
        raise ValueError(f"Year out of range: {year}")
    return date(year, 1, 1), date(year, 12, 31)


def parse_iso_week(spec: str) -> tuple[date, date]:
    """Convert 'YYYY-Www' (ISO 8601 week) to Monday..Sunday range."""
    m = re.match(r"^(\d{4})-[Ww](\d{1,2})$", spec.strip())
    if not m:
        raise ValueError(f"Invalid ISO week: {spec!r} (expected YYYY-Www)")
    year = int(m.group(1))
    week = int(m.group(2))
    # ISO week 1 contains the first Thursday; iso fromisocalendar handles edge cases.
    try:
        monday = date.fromisocalendar(year, week, 1)
    except ValueError as e:
        raise ValueError(f"Invalid ISO week: {spec!r}") from e
    sunday = monday + timedelta(days=6)
    return monday, sunday


def format_iso_week(d: date) -> str:
    """Format a date as its containing ISO week: 'YYYY-Www'."""
    y, w, _ = d.isocalendar()
    return f"{y}-w{w:02d}"


# ---------- aggregation primitives ----------

@dataclass(frozen=True)
class CashflowBucket:
    key: str           # category name | account name | merchant
    inflow: float      # sum of positive amounts
    outflow: float     # sum of |negative amounts| (reported positive)
    net: float         # inflow - outflow
    count: int


def _exclude_transfers_clause() -> str:
    """SQL fragment: exclude categories marked is_transfer. Transfers cancel to zero."""
    return (
        "(c.is_transfer IS NULL OR c.is_transfer = 0) "
        "AND (t.transfer_group_id IS NULL)"
    )


def cashflow_by(
    conn: sqlite3.Connection,
    start: date,
    end: date,
    *,
    by: str = "category",
    include_transfers: bool = False,
) -> list[CashflowBucket]:
    """Group transactions in [start, end] by category|account|merchant.

    Transfers are excluded by default (they net to zero at the household level).
    """
    if by not in ("category", "account", "merchant"):
        raise ValueError(f"Invalid `by`: {by!r}")

    key_expr = {
        "category": "COALESCE(c.name, '(uncategorized)')",
        "account": "a.name",
        "merchant": "COALESCE(t.merchant_normalized, t.description_raw)",
    }[by]

    base_where = "t.date BETWEEN ? AND ?"
    params: list = [start.isoformat(), end.isoformat()]
    if not include_transfers:
        base_where += " AND " + _exclude_transfers_clause()

    sql = f"""
        SELECT
            {key_expr} AS key,
            SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) AS inflow,
            SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS outflow,
            SUM(t.amount) AS net,
            COUNT(*) AS count
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        LEFT JOIN accounts a ON a.id = t.account_id
        WHERE {base_where}
        GROUP BY key
        ORDER BY outflow DESC, inflow DESC
    """
    rows = conn.execute(sql, params).fetchall()
    return [
        CashflowBucket(
            key=r["key"] or "(unknown)",
            inflow=float(r["inflow"] or 0.0),
            outflow=float(r["outflow"] or 0.0),
            net=float(r["net"] or 0.0),
            count=int(r["count"] or 0),
        )
        for r in rows
    ]


def cashflow_totals(
    conn: sqlite3.Connection,
    start: date,
    end: date,
    *,
    include_transfers: bool = False,
) -> dict:
    """Return totals for the window: inflow, outflow, net, txn_count."""
    base_where = "t.date BETWEEN ? AND ?"
    params: list = [start.isoformat(), end.isoformat()]
    if not include_transfers:
        base_where += " AND " + _exclude_transfers_clause()

    row = conn.execute(
        f"""
        SELECT
            SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) AS inflow,
            SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS outflow,
            SUM(t.amount) AS net,
            COUNT(*) AS count
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE {base_where}
        """,
        params,
    ).fetchone()
    return {
        "inflow": float(row["inflow"] or 0.0),
        "outflow": float(row["outflow"] or 0.0),
        "net": float(row["net"] or 0.0),
        "count": int(row["count"] or 0),
    }


# ---------- anomaly detection ----------

@dataclass(frozen=True)
class Anomaly:
    kind: str                # 'large_txn' | 'new_merchant' | 'category_over_pace' | 'missing_recurring'
    severity: str            # 'info' | 'warn' | 'alert'
    subject: str             # merchant / category / recurring pattern
    detail: str              # human-readable sentence
    amount: Optional[float] = None
    txn_id: Optional[int] = None
    date: Optional[str] = None


def detect_large_transactions(
    conn: sqlite3.Connection,
    start: date,
    end: date,
    *,
    threshold_dollars: float = 500.0,
    lookback_days: int = 180,
) -> list[Anomaly]:
    """Flag outflows whose amount is:
        (a) above `threshold_dollars` absolute, AND
        (b) materially larger than the median for the same merchant over the
            lookback window (>= 2x median, or first time that merchant has
            appeared with > $threshold).

    Transfers and known payroll/income rows are skipped.
    """
    window_start = (start - timedelta(days=lookback_days)).isoformat()

    candidates = conn.execute(
        """
        SELECT t.id, t.date, t.amount,
               COALESCE(t.merchant_normalized, t.description_raw) AS merchant,
               COALESCE(c.name, '(uncategorized)') AS category
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND t.amount <= ?
          AND (c.is_transfer IS NULL OR c.is_transfer = 0)
          AND (c.is_income IS NULL OR c.is_income = 0)
          AND t.transfer_group_id IS NULL
        ORDER BY t.amount ASC
        """,
        (start.isoformat(), end.isoformat(), -threshold_dollars),
    ).fetchall()

    anomalies: list[Anomaly] = []
    for c in candidates:
        hist = conn.execute(
            """
            SELECT -t.amount AS abs_amount
            FROM transactions t
            WHERE COALESCE(t.merchant_normalized, t.description_raw) = ?
              AND t.date BETWEEN ? AND ?
              AND t.id != ?
              AND t.amount < 0
            """,
            (c["merchant"], window_start, (start - timedelta(days=1)).isoformat(), c["id"]),
        ).fetchall()
        amt = abs(float(c["amount"]))
        if not hist:
            anomalies.append(Anomaly(
                kind="large_txn",
                severity="warn",
                subject=c["merchant"],
                detail=f"${amt:,.2f} at {c['merchant']} — first time over ${threshold_dollars:.0f} for this merchant.",
                amount=-amt,
                txn_id=int(c["id"]),
                date=c["date"],
            ))
            continue
        hist_amts = sorted(float(h["abs_amount"]) for h in hist)
        median = hist_amts[len(hist_amts) // 2]
        if median > 0 and amt >= 2 * median:
            anomalies.append(Anomaly(
                kind="large_txn",
                severity="warn",
                subject=c["merchant"],
                detail=(
                    f"${amt:,.2f} at {c['merchant']} — "
                    f"{amt/median:.1f}x typical (${median:,.2f})."
                ),
                amount=-amt,
                txn_id=int(c["id"]),
                date=c["date"],
            ))
    return anomalies


def detect_new_merchants(
    conn: sqlite3.Connection,
    start: date,
    end: date,
    *,
    lookback_days: int = 365,
    min_amount: float = 20.0,
) -> list[Anomaly]:
    """Merchants seen in [start, end] that were never seen in the prior
    `lookback_days`. Filters out tiny amounts to avoid noise.
    """
    window_start = (start - timedelta(days=lookback_days)).isoformat()
    rows = conn.execute(
        """
        SELECT
            COALESCE(t.merchant_normalized, t.description_raw) AS merchant,
            MIN(t.date) AS first_date,
            SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spent,
            COUNT(*) AS n
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND (c.is_transfer IS NULL OR c.is_transfer = 0)
          AND (c.is_income IS NULL OR c.is_income = 0)
          AND t.transfer_group_id IS NULL
        GROUP BY merchant
        HAVING spent >= ?
        """,
        (start.isoformat(), end.isoformat(), min_amount),
    ).fetchall()

    out: list[Anomaly] = []
    for r in rows:
        merchant = r["merchant"]
        prior = conn.execute(
            """
            SELECT 1 FROM transactions t
            WHERE COALESCE(t.merchant_normalized, t.description_raw) = ?
              AND t.date BETWEEN ? AND ?
            LIMIT 1
            """,
            (merchant, window_start, (start - timedelta(days=1)).isoformat()),
        ).fetchone()
        if prior is None:
            out.append(Anomaly(
                kind="new_merchant",
                severity="info",
                subject=merchant,
                detail=f"New merchant: {merchant} (${float(r['spent']):,.2f} across {int(r['n'])} txn).",
                amount=-float(r["spent"]),
                date=r["first_date"],
            ))
    return out


def detect_category_over_pace(
    conn: sqlite3.Connection,
    start: date,
    end: date,
    *,
    lookback_months: int = 3,
    min_dollars: float = 100.0,
    multiplier: float = 1.5,
) -> list[Anomaly]:
    """Flag categories where current-window outflow is materially above the
    prior `lookback_months` average over the equivalent window length.
    """
    window_days = (end - start).days + 1
    lookback_end = start - timedelta(days=1)
    lookback_start = lookback_end - timedelta(days=window_days * lookback_months)

    # Current window by category
    current = conn.execute(
        """
        SELECT
            COALESCE(c.name, '(uncategorized)') AS category,
            SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spent
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND (c.is_transfer IS NULL OR c.is_transfer = 0)
          AND (c.is_income IS NULL OR c.is_income = 0)
          AND t.transfer_group_id IS NULL
        GROUP BY category
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchall()

    out: list[Anomaly] = []
    for r in current:
        spent = float(r["spent"] or 0.0)
        if spent < min_dollars:
            continue
        prior = conn.execute(
            """
            SELECT SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spent
            FROM transactions t
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE t.date BETWEEN ? AND ?
              AND COALESCE(c.name, '(uncategorized)') = ?
              AND (c.is_transfer IS NULL OR c.is_transfer = 0)
              AND (c.is_income IS NULL OR c.is_income = 0)
              AND t.transfer_group_id IS NULL
            """,
            (lookback_start.isoformat(), lookback_end.isoformat(), r["category"]),
        ).fetchone()
        prior_total = float(prior["spent"] or 0.0)
        if prior_total <= 0:
            continue
        prior_avg_per_window = prior_total / lookback_months
        if prior_avg_per_window <= 0:
            continue
        if spent >= multiplier * prior_avg_per_window:
            out.append(Anomaly(
                kind="category_over_pace",
                severity="warn",
                subject=r["category"],
                detail=(
                    f"{r['category']} at ${spent:,.2f} — "
                    f"{spent/prior_avg_per_window:.1f}x typical (${prior_avg_per_window:,.2f})."
                ),
                amount=-spent,
            ))
    return out


def all_anomalies(
    conn: sqlite3.Connection,
    start: date,
    end: date,
) -> list[Anomaly]:
    """Run every detector and return a combined, deduplicated list."""
    out: list[Anomaly] = []
    out.extend(detect_large_transactions(conn, start, end))
    out.extend(detect_new_merchants(conn, start, end))
    out.extend(detect_category_over_pace(conn, start, end))
    # Stable sort: alert > warn > info, then by amount magnitude desc.
    severity_order = {"alert": 0, "warn": 1, "info": 2}
    out.sort(key=lambda a: (severity_order.get(a.severity, 99), -abs(a.amount or 0)))
    return out


# ---------- display helpers ----------

def anomaly_to_dict(a: Anomaly) -> dict:
    return {
        "kind": a.kind,
        "severity": a.severity,
        "subject": a.subject,
        "detail": a.detail,
        "amount": a.amount,
        "txn_id": a.txn_id,
        "date": a.date,
    }


def bucket_to_dict(b: CashflowBucket) -> dict:
    return {
        "key": b.key,
        "inflow": b.inflow,
        "outflow": b.outflow,
        "net": b.net,
        "count": b.count,
    }


# ---------- net worth at a point in time ----------

ASSET_TYPES = {"checking", "savings", "brokerage", "retirement", "cash", "other"}
LIABILITY_TYPES = {"credit_card", "loan", "mortgage"}


def networth_at(conn: sqlite3.Connection, as_of: date) -> dict:
    """Compute net worth using the most recent balance on or before `as_of`.

    Returns a dict with assets_total, liabilities_total, net_worth, and the
    per-account breakdown. Accounts with no balance on/before `as_of` are
    listed with balance=None.
    """
    accounts = conn.execute(
        "SELECT id, name, account_type FROM accounts WHERE active = 1 ORDER BY name"
    ).fetchall()
    assets = 0.0
    liabilities = 0.0
    breakdown = []
    oldest: Optional[str] = None
    for a in accounts:
        row = conn.execute(
            "SELECT as_of_date, balance FROM balance_history "
            "WHERE account_id = ? AND as_of_date <= ? "
            "ORDER BY as_of_date DESC LIMIT 1",
            (a["id"], as_of.isoformat()),
        ).fetchone()
        if row is None:
            breakdown.append({
                "account": a["name"],
                "account_type": a["account_type"],
                "balance": None,
                "as_of_date": None,
            })
            continue
        bal = float(row["balance"])
        if a["account_type"] in LIABILITY_TYPES:
            liabilities += bal
        else:
            assets += bal
        if oldest is None or row["as_of_date"] < oldest:
            oldest = row["as_of_date"]
        breakdown.append({
            "account": a["name"],
            "account_type": a["account_type"],
            "balance": bal,
            "as_of_date": row["as_of_date"],
        })
    return {
        "as_of": as_of.isoformat(),
        "assets_total": assets,
        "liabilities_total": liabilities,
        "net_worth": assets - liabilities,
        "oldest_balance_as_of": oldest,
        "breakdown": breakdown,
    }


# ---------- savings rate ----------

def savings_rate(conn: sqlite3.Connection, start: date, end: date) -> dict:
    """Compute savings rate for the window.

    Definition: (income_inflow - household_outflow) / income_inflow.
      - income_inflow: sum of positive amounts in categories flagged is_income,
        OR all positive amounts if no income categories are configured (fallback).
      - household_outflow: sum of absolute outflows, transfers excluded.

    Returns None when income_inflow is 0 (can't divide). A negative rate means
    the user spent more than they earned.
    """
    # Prefer explicitly-tagged income categories; fall back to all inflows.
    income_row = conn.execute(
        """
        SELECT SUM(t.amount) AS income
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND t.amount > 0
          AND c.is_income = 1
          AND t.transfer_group_id IS NULL
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchone()
    income = float(income_row["income"] or 0.0)
    if income == 0:
        # Fallback: all inflows excluding transfers.
        fallback_row = conn.execute(
            """
            SELECT SUM(t.amount) AS income
            FROM transactions t
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE t.date BETWEEN ? AND ?
              AND t.amount > 0
              AND (c.is_transfer IS NULL OR c.is_transfer = 0)
              AND t.transfer_group_id IS NULL
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchone()
        income = float(fallback_row["income"] or 0.0)

    outflow_row = conn.execute(
        """
        SELECT SUM(-t.amount) AS spent
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND t.amount < 0
          AND (c.is_transfer IS NULL OR c.is_transfer = 0)
          AND t.transfer_group_id IS NULL
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchone()
    spent = float(outflow_row["spent"] or 0.0)

    rate = None
    if income > 0:
        rate = (income - spent) / income

    return {
        "income": income,
        "spent": spent,
        "saved": income - spent,
        "rate": rate,
    }


# ---------- budget vs. actual ----------

def budget_vs_actual(conn: sqlite3.Connection, start: date, end: date) -> list[dict]:
    """For each category with an active budget in the window, compare
    planned to actual outflow.

    Returns a list of {category, planned, actual, variance, variance_pct}.
    Pro-rates monthly budgets when the window isn't a full calendar month.
    """
    window_days = (end - start).days + 1
    # Active budgets overlap with [start, end]
    rows = conn.execute(
        """
        SELECT bp.category_id, c.name AS category, bp.amount, bp.active_from, bp.active_to
        FROM budget_plan bp
        JOIN categories c ON c.id = bp.category_id
        WHERE bp.active_from <= ?
          AND (bp.active_to IS NULL OR bp.active_to >= ?)
        """,
        (end.isoformat(), start.isoformat()),
    ).fetchall()
    out: list[dict] = []
    for r in rows:
        # Assume budget amount is monthly; pro-rate for windows != ~30d.
        planned = float(r["amount"]) * (window_days / 30.0)
        actual_row = conn.execute(
            """
            SELECT SUM(-t.amount) AS spent
            FROM transactions t
            WHERE t.date BETWEEN ? AND ?
              AND t.category_id = ?
              AND t.amount < 0
              AND t.transfer_group_id IS NULL
            """,
            (start.isoformat(), end.isoformat(), r["category_id"]),
        ).fetchone()
        actual = float(actual_row["spent"] or 0.0)
        variance = actual - planned
        variance_pct = (variance / planned * 100) if planned else None
        out.append({
            "category": r["category"],
            "planned": round(planned, 2),
            "actual": round(actual, 2),
            "variance": round(variance, 2),
            "variance_pct": round(variance_pct, 1) if variance_pct is not None else None,
        })
    # Sort worst-variance first.
    out.sort(key=lambda d: -d["variance"])
    return out


# ---------- goal progress ----------

def goal_progress(conn: sqlite3.Connection, as_of: date) -> list[dict]:
    """Return per-goal progress with red/yellow/green pace classification.

    status logic:
      - If no target_date or no target_amount: status='info' (can't judge pace).
      - green: on/ahead of linear pace toward target by target_date.
      - yellow: behind pace but within 20%.
      - red: behind pace by more than 20%, or target date is in the past and
        goal not completed.
    """
    goals = conn.execute(
        "SELECT id, name, target_amount, target_date, priority, status, notes "
        "FROM goals WHERE status = 'active' ORDER BY priority, name"
    ).fetchall()
    out: list[dict] = []
    for g in goals:
        # Latest progress on or before `as_of`.
        prog_row = conn.execute(
            "SELECT amount, as_of_date FROM goals_progress "
            "WHERE goal_id = ? AND as_of_date <= ? "
            "ORDER BY as_of_date DESC LIMIT 1",
            (g["id"], as_of.isoformat()),
        ).fetchone()
        current = float(prog_row["amount"]) if prog_row else 0.0
        current_as_of = prog_row["as_of_date"] if prog_row else None

        target_amount = float(g["target_amount"]) if g["target_amount"] is not None else None
        target_date = g["target_date"]

        status = "info"
        expected = None
        if target_amount and target_date:
            try:
                td = date.fromisoformat(target_date)
                # Assume start-of-goal is the earliest progress entry; fall
                # back to today-as-start if none.
                start_row = conn.execute(
                    "SELECT MIN(as_of_date) AS first_date FROM goals_progress WHERE goal_id = ?",
                    (g["id"],),
                ).fetchone()
                start_date_str = start_row["first_date"] if start_row["first_date"] else as_of.isoformat()
                start_date = date.fromisoformat(start_date_str)
                total_days = max(1, (td - start_date).days)
                elapsed = max(0, (as_of - start_date).days)
                expected = target_amount * min(1.0, elapsed / total_days)
                if td < as_of and current < target_amount:
                    status = "red"
                elif current >= expected:
                    status = "green"
                elif expected > 0 and current >= 0.8 * expected:
                    status = "yellow"
                else:
                    status = "red"
            except ValueError:
                status = "info"

        out.append({
            "id": int(g["id"]),
            "name": g["name"],
            "target_amount": target_amount,
            "target_date": target_date,
            "priority": int(g["priority"]),
            "current": current,
            "current_as_of": current_as_of,
            "expected_at_pace": round(expected, 2) if expected is not None else None,
            "status": status,
        })
    return out


# ---------- advisory helpers (Phase 9) ----------

# Account types that act as accessible cash for affordability purposes.
LIQUID_ASSET_TYPES = {"checking", "savings", "cash"}

# Default mapping from account_type to asset_class when accounts.asset_class is
# unset. Users can override per-account via `account edit --asset-class`.
DEFAULT_ASSET_CLASS_BY_TYPE = {
    "checking": "cash",
    "savings": "cash",
    "cash": "cash",
    "brokerage": "us_stocks",     # opinionated default; edit if needed
    "retirement": "us_stocks",
    "credit_card": "liability",
    "loan": "liability",
    "mortgage": "liability",
    "other": "other",
}


def liquid_cash(conn: sqlite3.Connection, as_of: date) -> dict:
    """Sum of latest balances on/before `as_of` across liquid account types.

    Uses `LIQUID_ASSET_TYPES` (checking/savings/cash). Returns total plus a
    breakdown list so the advisor can cite *which* accounts contributed.
    """
    rows = conn.execute(
        "SELECT id, name, account_type FROM accounts "
        "WHERE active = 1 AND account_type IN (" +
        ",".join("?" for _ in LIQUID_ASSET_TYPES) + ") "
        "ORDER BY name",
        tuple(sorted(LIQUID_ASSET_TYPES)),
    ).fetchall()

    total = 0.0
    breakdown = []
    oldest: Optional[str] = None
    for r in rows:
        bal_row = conn.execute(
            "SELECT as_of_date, balance FROM balance_history "
            "WHERE account_id = ? AND as_of_date <= ? "
            "ORDER BY as_of_date DESC LIMIT 1",
            (r["id"], as_of.isoformat()),
        ).fetchone()
        if bal_row is None:
            breakdown.append({
                "account": r["name"],
                "account_type": r["account_type"],
                "balance": None,
                "as_of_date": None,
            })
            continue
        bal = float(bal_row["balance"])
        total += bal
        if oldest is None or bal_row["as_of_date"] < oldest:
            oldest = bal_row["as_of_date"]
        breakdown.append({
            "account": r["name"],
            "account_type": r["account_type"],
            "balance": bal,
            "as_of_date": bal_row["as_of_date"],
        })
    return {
        "as_of": as_of.isoformat(),
        "total": round(total, 2),
        "oldest_balance_as_of": oldest,
        "breakdown": breakdown,
    }


def trailing_monthly_outflow(
    conn: sqlite3.Connection,
    as_of: date,
    *,
    months: int = 3,
) -> dict:
    """Average monthly outflow over the trailing `months` months ending at
    the end of the month before `as_of` (so the current partial month doesn't
    skew the average).

    Returns `{months, start, end, total_outflow, monthly_average}`.
    Transfers and tagged income are excluded (same rule as cashflow totals).
    """
    # End-of-previous month
    first_of_current = date(as_of.year, as_of.month, 1)
    end = first_of_current - timedelta(days=1)
    # Go back `months` full months from that end
    year = end.year
    month = end.month - months + 1
    while month <= 0:
        month += 12
        year -= 1
    start = date(year, month, 1)

    row = conn.execute(
        """
        SELECT SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS spent
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND (c.is_transfer IS NULL OR c.is_transfer = 0)
          AND t.transfer_group_id IS NULL
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchone()
    total = float(row["spent"] or 0.0)
    avg = total / months if months > 0 else 0.0
    return {
        "months": months,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "total_outflow": round(total, 2),
        "monthly_average": round(avg, 2),
    }


@dataclass(frozen=True)
class Debt:
    account_id: int
    name: str
    account_type: str        # 'credit_card' | 'loan' | 'mortgage'
    balance: float           # positive magnitude
    apr: Optional[float]     # percent, e.g. 24.99
    min_payment: Optional[float]
    as_of_date: Optional[str]


def debt_roster(conn: sqlite3.Connection, as_of: date) -> list[Debt]:
    """Every active liability-type account with its latest balance on/before
    `as_of`, APR, and min payment.

    Accounts with no recorded balance are skipped — the advisor can flag that
    separately. Balances are reported as positive magnitudes so payoff math
    is unambiguous.
    """
    rows = conn.execute(
        "SELECT id, name, account_type, apr, min_payment FROM accounts "
        "WHERE active = 1 AND account_type IN ('credit_card', 'loan', 'mortgage') "
        "ORDER BY name"
    ).fetchall()
    out: list[Debt] = []
    for r in rows:
        bal_row = conn.execute(
            "SELECT as_of_date, balance FROM balance_history "
            "WHERE account_id = ? AND as_of_date <= ? "
            "ORDER BY as_of_date DESC LIMIT 1",
            (r["id"], as_of.isoformat()),
        ).fetchone()
        if bal_row is None:
            continue
        bal = abs(float(bal_row["balance"]))
        out.append(Debt(
            account_id=int(r["id"]),
            name=r["name"],
            account_type=r["account_type"],
            balance=bal,
            apr=float(r["apr"]) if r["apr"] is not None else None,
            min_payment=float(r["min_payment"]) if r["min_payment"] is not None else None,
            as_of_date=bal_row["as_of_date"],
        ))
    return out


def simulate_payoff(
    debts: list[Debt],
    *,
    strategy: str = "avalanche",
    extra_monthly: float = 0.0,
    custom_order: Optional[list[str]] = None,
    max_months: int = 600,
) -> dict:
    """Simulate month-by-month payoff under the given strategy.

    Strategies:
      - 'avalanche': pay min on all, throw extra at highest-APR first.
      - 'snowball':  pay min on all, throw extra at smallest-balance first.
      - 'custom':    use `custom_order` (list of account names) for priority.

    Debts missing APR are treated as 0% (documented in output). Debts missing
    min_payment are treated as 2% of balance floor $25 (standard credit-card
    approximation) — the caller gets a `warnings` list describing every
    assumption we made.

    Returns `{months, total_interest, total_paid, by_debt: [...], warnings}`.
    The `by_debt` list contains `{name, months_to_zero, interest_paid}`.
    Caps at `max_months` (50 years) to stop infinite loops when payments
    don't cover interest — in that case `converged: False`.
    """
    if strategy not in ("avalanche", "snowball", "custom"):
        raise ValueError(f"Unknown strategy: {strategy!r}")
    if strategy == "custom" and not custom_order:
        raise ValueError("custom strategy requires custom_order")

    warnings: list[str] = []
    # Snapshot into mutable dicts we can iterate over.
    state = []
    for d in debts:
        apr = d.apr
        if apr is None:
            warnings.append(f"{d.name}: no APR set — treating as 0% for simulation.")
            apr = 0.0
        min_pmt = d.min_payment
        if min_pmt is None:
            est = max(25.0, 0.02 * d.balance)
            warnings.append(
                f"{d.name}: no min_payment set — using 2% of balance (floor $25) = ${est:.2f}."
            )
            min_pmt = est
        state.append({
            "name": d.name,
            "balance": float(d.balance),
            "apr": float(apr),
            "min_payment": float(min_pmt),
            "months_to_zero": None,
            "interest_paid": 0.0,
        })

    def _priority_key(row: dict) -> tuple:
        if strategy == "avalanche":
            # Higher APR first, then larger balance.
            return (-row["apr"], -row["balance"])
        if strategy == "snowball":
            # Smaller balance first, then higher APR.
            return (row["balance"], -row["apr"])
        # custom
        try:
            idx = custom_order.index(row["name"])
        except ValueError:
            idx = len(custom_order)
        return (idx, -row["apr"])

    months = 0
    total_interest = 0.0
    total_paid = 0.0
    extra = float(extra_monthly)

    while any(d["balance"] > 0.005 for d in state):
        months += 1
        if months > max_months:
            return {
                "strategy": strategy,
                "converged": False,
                "months": months - 1,
                "total_interest": round(total_interest, 2),
                "total_paid": round(total_paid, 2),
                "by_debt": [
                    {
                        "name": d["name"],
                        "months_to_zero": d["months_to_zero"],
                        "interest_paid": round(d["interest_paid"], 2),
                        "remaining_balance": round(d["balance"], 2),
                    }
                    for d in state
                ],
                "warnings": warnings + [
                    f"Simulation did not converge within {max_months} months — "
                    "extra payment is too small to cover interest."
                ],
                "extra_monthly": extra,
            }
        # 1. Accrue monthly interest.
        for d in state:
            if d["balance"] <= 0:
                continue
            monthly_rate = d["apr"] / 100.0 / 12.0
            interest = d["balance"] * monthly_rate
            d["balance"] += interest
            d["interest_paid"] += interest
            total_interest += interest

        # 2. Pay minimums.
        budget_remaining = extra
        for d in state:
            if d["balance"] <= 0:
                continue
            pay = min(d["min_payment"], d["balance"])
            d["balance"] -= pay
            total_paid += pay
            if d["balance"] <= 0 and d["months_to_zero"] is None:
                d["months_to_zero"] = months
                # Freed-up min payment rolls into the extra bucket next month.
                extra += d["min_payment"]

        # 3. Apply extra in priority order.
        active = [d for d in state if d["balance"] > 0]
        active.sort(key=_priority_key)
        for d in active:
            if budget_remaining <= 0:
                break
            pay = min(budget_remaining, d["balance"])
            d["balance"] -= pay
            total_paid += pay
            budget_remaining -= pay
            if d["balance"] <= 0 and d["months_to_zero"] is None:
                d["months_to_zero"] = months
                extra += d["min_payment"]

    return {
        "strategy": strategy,
        "converged": True,
        "months": months,
        "total_interest": round(total_interest, 2),
        "total_paid": round(total_paid, 2),
        "by_debt": [
            {
                "name": d["name"],
                "months_to_zero": d["months_to_zero"],
                "interest_paid": round(d["interest_paid"], 2),
                "remaining_balance": round(d["balance"], 2),
            }
            for d in state
        ],
        "warnings": warnings,
        "extra_monthly": extra_monthly,
    }


def current_allocation(conn: sqlite3.Connection, as_of: date) -> dict:
    """Group latest balances by asset class and report percent-of-assets.

    Uses `accounts.asset_class` when set; otherwise falls back to
    `DEFAULT_ASSET_CLASS_BY_TYPE[account_type]`. Liability accounts (and
    accounts explicitly tagged `liability`) are excluded from the allocation
    total — allocation is about the investable side of the balance sheet.

    Returns:
        {
            as_of, assets_total,
            by_class: [{asset_class, balance, pct, accounts: [names]}],
            missing_balance: [account names]
        }
    """
    rows = conn.execute(
        "SELECT id, name, account_type, asset_class FROM accounts WHERE active = 1 ORDER BY name"
    ).fetchall()

    totals: dict[str, float] = {}
    contributors: dict[str, list[str]] = {}
    missing: list[str] = []
    assets_total = 0.0

    for r in rows:
        asset_class = r["asset_class"] or DEFAULT_ASSET_CLASS_BY_TYPE.get(
            r["account_type"], "other"
        )
        # Skip liabilities from the allocation total.
        if asset_class == "liability" or r["account_type"] in (
            "credit_card", "loan", "mortgage"
        ):
            continue

        bal_row = conn.execute(
            "SELECT balance FROM balance_history "
            "WHERE account_id = ? AND as_of_date <= ? "
            "ORDER BY as_of_date DESC LIMIT 1",
            (r["id"], as_of.isoformat()),
        ).fetchone()
        if bal_row is None:
            missing.append(r["name"])
            continue
        bal = float(bal_row["balance"])
        if bal <= 0:
            # Zero/negative balances on the asset side: ignore — a zeroed
            # account doesn't belong in the allocation pie.
            continue
        totals[asset_class] = totals.get(asset_class, 0.0) + bal
        contributors.setdefault(asset_class, []).append(r["name"])
        assets_total += bal

    by_class = []
    for ac in sorted(totals.keys()):
        pct = (totals[ac] / assets_total * 100.0) if assets_total > 0 else 0.0
        by_class.append({
            "asset_class": ac,
            "balance": round(totals[ac], 2),
            "pct": round(pct, 2),
            "accounts": contributors[ac],
        })
    return {
        "as_of": as_of.isoformat(),
        "assets_total": round(assets_total, 2),
        "by_class": by_class,
        "missing_balance": missing,
    }


def allocation_targets(conn: sqlite3.Connection, as_of: date) -> dict:
    """Return the active target allocation — the latest row per asset_class
    whose `active_from <= as_of`.

    Returns `{as_of, targets: {asset_class: pct}, total_pct}`. An empty dict
    means no targets have been set yet.
    """
    rows = conn.execute(
        """
        SELECT asset_class, target_pct, active_from
        FROM allocation_targets
        WHERE active_from <= ?
        ORDER BY asset_class, active_from DESC
        """,
        (as_of.isoformat(),),
    ).fetchall()
    targets: dict[str, float] = {}
    for r in rows:
        ac = r["asset_class"]
        if ac not in targets:
            targets[ac] = float(r["target_pct"])
    total = sum(targets.values())
    return {
        "as_of": as_of.isoformat(),
        "targets": {k: round(v, 2) for k, v in sorted(targets.items())},
        "total_pct": round(total, 2),
    }


def goal_pace_impact(
    conn: sqlite3.Connection,
    as_of: date,
    *,
    reduction: float,
) -> list[dict]:
    """For each active goal with a monthly pace expectation, estimate how many
    extra months the given `reduction` (dollars pulled from future savings)
    would add before it's made back up.

    This is a rough estimator used by `finance afford`: it assumes the user's
    trailing monthly outflow stays constant and any dollar spent on the
    purchase is a dollar *not* going to goals. The impact is spread
    proportionally across *active* goals by priority.

    Returns `[{goal, extra_months_to_target, monthly_pace_needed}]` — only
    goals with target_amount and target_date populated.
    """
    goals = goal_progress(conn, as_of)
    active = [g for g in goals if g["target_amount"] and g["target_date"]]
    if not active:
        return []

    # Weight by inverse priority (priority 1 = highest, gets the most weight).
    weights = [1.0 / max(1, int(g["priority"])) for g in active]
    wsum = sum(weights) or 1.0
    out = []
    for g, w in zip(active, weights):
        share = reduction * (w / wsum)
        try:
            td = date.fromisoformat(g["target_date"])
        except ValueError:
            continue
        months_left = max(1, (td.year - as_of.year) * 12 + (td.month - as_of.month))
        needed = max(0.0, g["target_amount"] - (g["current"] or 0.0))
        monthly_pace_needed = needed / months_left if months_left else needed
        # Extra months = share / monthly_pace_needed (if pace is meaningful).
        extra_months = share / monthly_pace_needed if monthly_pace_needed > 0 else None
        out.append({
            "goal": g["name"],
            "priority": g["priority"],
            "share_of_reduction": round(share, 2),
            "monthly_pace_needed": round(monthly_pace_needed, 2),
            "extra_months_to_target": round(extra_months, 1) if extra_months is not None else None,
        })
    return out



# ---------- fee audit (Phase 10) ----------

def fee_audit(
    conn: sqlite3.Connection,
    as_of: date,
    *,
    threshold_pct: float = 0.25,
) -> dict:
    """Scan active accounts for recorded fees and flag expensive ones.

    Looks at two user-recorded fields on the `accounts` table:
      - `expense_ratio_pct` (e.g., 0.03 for a 0.03% index fund)
      - `annual_fee` (flat dollars)

    For each account with at least one populated, computes an estimated
    annual fee cost using the most-recent balance on/before `as_of`:

        expense_cost = balance * (expense_ratio_pct / 100)
        annual_cost  = expense_cost + annual_fee

    Returns per-account rows plus a `flagged` list where
    `expense_ratio_pct > threshold_pct` — the rough Boglehead mark for
    "this is costing you." Accounts with no recorded fees are skipped
    silently (not an error).
    """
    rows = conn.execute(
        """
        SELECT id, name, account_type, expense_ratio_pct, annual_fee
        FROM accounts
        WHERE active = 1
          AND (expense_ratio_pct IS NOT NULL OR annual_fee IS NOT NULL)
        ORDER BY name
        """,
    ).fetchall()

    audited = []
    flagged = []
    total_annual_cost = 0.0

    for r in rows:
        bal_row = conn.execute(
            "SELECT as_of_date, balance FROM balance_history "
            "WHERE account_id = ? AND as_of_date <= ? "
            "ORDER BY as_of_date DESC LIMIT 1",
            (r["id"], as_of.isoformat()),
        ).fetchone()
        balance = float(bal_row["balance"]) if bal_row else None
        balance_as_of = bal_row["as_of_date"] if bal_row else None

        expense_ratio = r["expense_ratio_pct"]
        annual_fee = r["annual_fee"]

        expense_cost: Optional[float] = None
        if expense_ratio is not None and balance is not None:
            # ER is stored as a percent; e.g., 0.03 means 0.03%.
            expense_cost = float(balance) * float(expense_ratio) / 100.0

        flat_fee = float(annual_fee) if annual_fee is not None else 0.0
        total_cost = (expense_cost or 0.0) + flat_fee
        total_annual_cost += total_cost

        row = {
            "account": r["name"],
            "account_type": r["account_type"],
            "balance": round(balance, 2) if balance is not None else None,
            "balance_as_of": balance_as_of,
            "expense_ratio_pct": (
                round(float(expense_ratio), 4) if expense_ratio is not None else None
            ),
            "annual_fee": round(flat_fee, 2) if annual_fee is not None else None,
            "expense_cost": (
                round(expense_cost, 2) if expense_cost is not None else None
            ),
            "total_annual_cost": round(total_cost, 2),
        }
        audited.append(row)

        if expense_ratio is not None and float(expense_ratio) > threshold_pct:
            flagged.append(row)

    # Accounts without any fee info — surface so the advisor can nudge the
    # user to populate them when next convenient.
    missing_rows = conn.execute(
        """
        SELECT name
        FROM accounts
        WHERE active = 1
          AND expense_ratio_pct IS NULL
          AND annual_fee IS NULL
          AND account_type IN ('brokerage', 'retirement')
        ORDER BY name
        """
    ).fetchall()
    missing_fee_info = [r["name"] for r in missing_rows]

    audited.sort(key=lambda a: -a["total_annual_cost"])
    flagged.sort(key=lambda a: -(a["expense_ratio_pct"] or 0.0))

    return {
        "as_of": as_of.isoformat(),
        "threshold_pct": threshold_pct,
        "accounts": audited,
        "flagged": flagged,
        "total_annual_cost": round(total_annual_cost, 2),
        "missing_fee_info": missing_fee_info,
    }


# ---------- tax pack (Phase 10) ----------

def tax_pack(conn: sqlite3.Connection, year: int) -> dict:
    """Produce a handoff bundle of the year's tax-relevant aggregates.

    This is a *data pack*, not tax advice. Numbers only — the AI advisor
    (and ultimately a CPA or filing software) interprets them.

    Included:
      - income: totals from categories flagged is_income; breakdown per
        income category
      - spend_by_category: full per-category outflow (transfers excluded).
        The advisor surfaces the rows that tend to affect filing
        (medical, charitable, mortgage_interest, state_tax, etc.) but
        we do not classify them here — the category name is ground truth.
      - net_worth: Jan 1 and Dec 31 snapshot (via networth_at)
      - account_ids: simple roster for audit trails
      - notable: convenience list of tax-relevant category matches using
        common naming conventions. The advisor should still verify
        the user's actual taxonomy in `transactions/categories.md`.

    Numbers are pre-tax. We do not estimate tax owed, contribution
    limits, or withholding adequacy — refer those to a CPA.
    """
    try:
        start, end = parse_year(str(year))
    except ValueError as e:
        raise ValueError(f"Invalid year for tax_pack: {year!r}") from e

    # Income (tagged is_income=1)
    income_rows = conn.execute(
        """
        SELECT c.name AS category, SUM(t.amount) AS total, COUNT(*) AS n
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND t.amount > 0
          AND c.is_income = 1
          AND t.transfer_group_id IS NULL
        GROUP BY c.id
        ORDER BY total DESC
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    income_total = sum(float(r["total"] or 0) for r in income_rows)
    income_by_source = [
        {
            "category": r["category"],
            "total": round(float(r["total"] or 0), 2),
            "count": int(r["n"]),
        }
        for r in income_rows
    ]

    # Spending by category (full, worst-first by outflow)
    spend_rows = conn.execute(
        """
        SELECT c.name AS category, SUM(-t.amount) AS spent, COUNT(*) AS n
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND t.amount < 0
          AND (c.is_transfer IS NULL OR c.is_transfer = 0)
          AND t.transfer_group_id IS NULL
        GROUP BY c.id
        ORDER BY spent DESC
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    spend_by_category = [
        {
            "category": r["category"] or "(uncategorized)",
            "total": round(float(r["spent"] or 0), 2),
            "count": int(r["n"]),
        }
        for r in spend_rows
    ]

    # Net worth anchors
    # Beginning: Dec 31 of prior year (balance on or before that date)
    nw_begin = networth_at(conn, date(start.year - 1, 12, 31))
    nw_end = networth_at(conn, end)
    nw_delta = nw_end["net_worth"] - nw_begin["net_worth"]

    # Notable tax-relevant category matches (by substring, case-insensitive)
    notable_keys = (
        ("charitable", "donation"),
        ("medical", "healthcare", "health"),
        ("mortgage_interest", "mortgage"),
        ("state_tax", "property_tax", "tax"),
        ("hsa",),
        ("ira", "roth", "401k"),
        ("student_loan_interest", "student_loan"),
    )
    notable: dict[str, list[dict]] = {}
    for keys in notable_keys:
        label = keys[0]
        matches = []
        for row in spend_by_category + [
            # also check income tables in case of refunds/distributions tagged odd
            {"category": r["category"], "total": r["total"], "count": r["count"]}
            for r in income_by_source
        ]:
            name = (row["category"] or "").lower()
            if any(k in name for k in keys):
                matches.append(row)
        if matches:
            notable[label] = matches

    return {
        "year": int(year),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "income": {
            "total": round(income_total, 2),
            "by_source": income_by_source,
        },
        "spend_by_category": spend_by_category,
        "net_worth": {
            "beginning": round(nw_begin["net_worth"], 2),
            "beginning_as_of": nw_begin["oldest_balance_as_of"],
            "ending": round(nw_end["net_worth"], 2),
            "ending_as_of": nw_end["oldest_balance_as_of"],
            "delta": round(nw_delta, 2),
        },
        "notable": notable,
        "disclaimer": (
            "Pre-tax totals only. No filing advice; no tax liability "
            "estimate. Refer to a CPA or filing software."
        ),
    }


# ---------- mode detection (Phase 11) ----------

# High-APR threshold for "problem" debt. Mortgages are excluded regardless
# because mortgages are leverage against an appreciating asset, not a debt
# crisis. The 8% mark is a rough proxy: above it, mathematically you're
# almost always better off paying down than investing a diversified portfolio.
HIGH_APR_THRESHOLD = 8.0


def mode_detect(conn: sqlite3.Connection, as_of: date) -> dict:
    """Classify the user into one of three behavioral modes.

    The advisor uses the returned `mode` to shift tone and prioritization:

      - 'debt'     — high-APR consumer debt is the binding constraint.
                     Advice should push every extra dollar toward payoff
                     until the high-APR balance is zero.
      - 'invest'   — no problematic debt, emergency fund is adequate,
                     allocation targets are set. Advice should focus on
                     tax-advantaged contributions, rebalance discipline,
                     and long-term compounding.
      - 'balanced' — everything else (most users, most of the time).
                     Advice balances debt paydown, emergency fund, and
                     investing.

    Heuristic inputs (all read from the DB — no estimates):
      - `high_apr_debt_total`: sum of credit_card/loan balances with APR
        >= HIGH_APR_THRESHOLD (mortgages excluded).
      - `emergency_fund_months`: liquid cash / trailing 3-month average
        outflow. 3+ months = adequate for the 'invest' branch.
      - `allocation_targets_set`: at least one row in allocation_targets
        active as of today.

    Returns:
        {
            mode: 'debt' | 'invest' | 'balanced',
            reasons: [str, ...],     # human-readable "why this mode"
            inputs: {                # the inputs the decision was based on
                high_apr_debt_total, high_apr_accounts: [...],
                liquid_cash, monthly_outflow_avg,
                emergency_fund_months, emergency_fund_months_target,
                allocation_targets_set,
            },
            as_of: 'YYYY-MM-DD',
        }
    """
    # --- High-APR debt ---
    debts = debt_roster(conn, as_of)
    high_apr = [
        d for d in debts
        if d.account_type != "mortgage"
        and d.apr is not None
        and d.apr >= HIGH_APR_THRESHOLD
    ]
    high_apr_total = sum(d.balance for d in high_apr)
    high_apr_accounts = [
        {
            "name": d.name,
            "account_type": d.account_type,
            "balance": round(d.balance, 2),
            "apr": d.apr,
        }
        for d in high_apr
    ]

    # --- Emergency fund months ---
    cash = liquid_cash(conn, as_of)
    outflow = trailing_monthly_outflow(conn, as_of, months=3)
    monthly_avg = outflow["monthly_average"]
    cash_total = cash["total"]
    # Target: 3 months (entry criterion for 'invest' mode). Users can raise
    # the bar in their own `rules.md`; the detector uses 3 as a floor.
    ef_target_months = 3.0
    if monthly_avg > 0:
        ef_months = cash_total / monthly_avg
    else:
        # No recorded outflow yet — we can't say the fund is "adequate" or
        # not. Treat as None so the mode logic below doesn't claim invest-mode
        # without evidence.
        ef_months = None

    # --- Allocation targets ---
    targets = allocation_targets(conn, as_of)
    targets_set = bool(targets["targets"])

    # --- Decide ---
    reasons: list[str] = []
    if high_apr_total > 0:
        mode = "debt"
        names = ", ".join(d.name for d in high_apr) or "high-APR debt"
        reasons.append(
            f"High-APR debt present: {names} totaling "
            f"${high_apr_total:,.2f} at >= {HIGH_APR_THRESHOLD:.1f}% APR."
        )
    elif (
        ef_months is not None
        and ef_months >= ef_target_months
        and targets_set
    ):
        mode = "invest"
        reasons.append("No high-APR debt.")
        reasons.append(
            f"Emergency fund is {ef_months:.1f} months of average outflow "
            f"(target: {ef_target_months:.0f})."
        )
        reasons.append("Allocation targets are set.")
    else:
        mode = "balanced"
        reasons.append("No high-APR debt.")
        if ef_months is None:
            reasons.append(
                "Can't assess emergency fund yet — no recorded outflow "
                "in the trailing 3 months."
            )
        elif ef_months < ef_target_months:
            short = ef_target_months - ef_months
            reasons.append(
                f"Emergency fund is {ef_months:.1f} months "
                f"(~{short:.1f} months short of the 3-month floor)."
            )
        if not targets_set:
            reasons.append("Allocation targets are not yet set.")

    return {
        "as_of": as_of.isoformat(),
        "mode": mode,
        "reasons": reasons,
        "inputs": {
            "high_apr_debt_total": round(high_apr_total, 2),
            "high_apr_threshold_pct": HIGH_APR_THRESHOLD,
            "high_apr_accounts": high_apr_accounts,
            "liquid_cash": cash_total,
            "monthly_outflow_avg": monthly_avg,
            "emergency_fund_months": (
                round(ef_months, 2) if ef_months is not None else None
            ),
            "emergency_fund_target_months": ef_target_months,
            "allocation_targets_set": targets_set,
        },
    }


# ---------- recurring / automation audit (Phase 11) ----------

def detect_recurring(
    conn: sqlite3.Connection,
    as_of: date,
    *,
    lookback_months: int = 6,
    min_hits: int = 3,
    amount_tolerance: float = 0.15,
) -> list[dict]:
    """Surface recurring outflows — the candidates for an automation audit.

    A "recurring" pattern is a merchant that shows an outflow at roughly the
    same cadence (monthly-ish) for at least `min_hits` distinct months within
    the lookback window, where successive charges are within
    `amount_tolerance` of each other (default ±15%).

    Transfers and income are excluded. Returns a list sorted by estimated
    annualized cost descending.

    Each row:
        {
            merchant, category, hits (int), months_seen: [YYYY-MM, ...],
            median_amount, last_amount, last_date,
            estimated_monthly, estimated_annual,
        }
    """
    # Window: the last `lookback_months` full months ending at the end of the
    # month before `as_of` (so the current partial month doesn't skew).
    first_of_current = date(as_of.year, as_of.month, 1)
    end = first_of_current - timedelta(days=1)
    year = end.year
    month = end.month - lookback_months + 1
    while month <= 0:
        month += 12
        year -= 1
    start = date(year, month, 1)

    rows = conn.execute(
        """
        SELECT
            COALESCE(t.merchant_normalized, t.description_raw) AS merchant,
            COALESCE(c.name, '(uncategorized)') AS category,
            t.date,
            -t.amount AS spent
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND t.amount < 0
          AND (c.is_transfer IS NULL OR c.is_transfer = 0)
          AND (c.is_income IS NULL OR c.is_income = 0)
          AND t.transfer_group_id IS NULL
        ORDER BY merchant, t.date
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchall()

    # Group by merchant.
    by_merchant: dict[str, list[dict]] = {}
    for r in rows:
        m = r["merchant"] or "(unknown)"
        by_merchant.setdefault(m, []).append({
            "date": r["date"],
            "amount": float(r["spent"] or 0),
            "category": r["category"],
        })

    out: list[dict] = []
    for merchant, charges in by_merchant.items():
        if len(charges) < min_hits:
            continue
        # Bucket by month-of-charge; recurring means distinct months, not
        # duplicate same-day charges.
        months_seen: list[str] = []
        for c in charges:
            ym = c["date"][:7]  # 'YYYY-MM'
            if ym not in months_seen:
                months_seen.append(ym)
        if len(months_seen) < min_hits:
            continue
        # Amount stability check — sort charges, take median, require that
        # at least (hits - 1) of them are within tolerance of the median.
        amounts = sorted(c["amount"] for c in charges)
        mid = amounts[len(amounts) // 2]
        if mid <= 0:
            continue
        within = sum(1 for a in amounts if abs(a - mid) / mid <= amount_tolerance)
        if within < min_hits:
            continue
        last = charges[-1]
        estimated_monthly = round(mid, 2)
        out.append({
            "merchant": merchant,
            "category": charges[0]["category"],
            "hits": len(charges),
            "months_seen": months_seen,
            "median_amount": round(mid, 2),
            "last_amount": round(last["amount"], 2),
            "last_date": last["date"],
            "estimated_monthly": estimated_monthly,
            "estimated_annual": round(estimated_monthly * 12, 2),
        })

    out.sort(key=lambda r: -r["estimated_annual"])
    return out
