"""Advisor insights — the kind of things a financial advisor would tell you.

Each generator examines the current financial state and produces structured
observations. Insights persist in the database until dismissed or until the
underlying condition changes.

Design:
  - Generators are pure functions: (conn, as_of) -> list[dict].
  - Each insight has a stable `insight_key` for dedup.
  - `sync_insights` upserts into the `insights` table — new insights are
    inserted, changed insights are updated, and conditions that no longer
    hold are marked `is_current=0`.
  - Dismissed insights stay dismissed; the user doesn't see them again
    unless the key naturally changes (e.g., a different account enters
    high-APR territory).
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from finance_advisor.analytics import (
    current_allocation,
    allocation_targets,
    debt_roster,
    detect_category_over_pace,
    detect_recurring,
    goal_progress,
    mode_detect,
    networth_at,
    parse_window,
    savings_rate,
    HIGH_APR_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_insights(conn: sqlite3.Connection, as_of: date) -> list[dict]:
    """Run all insight generators and return a combined list.

    Each insight dict contains:
        insight_key  — stable identifier for dedup
        type         — category (debt, spending, savings, networth, goals, etc.)
        severity     — positive | info | warn | alert
        title        — short headline
        body         — one-sentence advisor observation
        source       — which generator produced it
    """
    # Pre-compute shared data used by multiple generators.
    nw = networth_at(conn, as_of)
    md = mode_detect(conn, as_of)

    generators = [
        lambda: _insight_debt_interest(conn, as_of),
        lambda: _insight_emergency_fund(md),
        lambda: _insight_savings_rate(conn, as_of),
        lambda: _insight_goals_pace(conn, as_of),
        lambda: _insight_goal_milestones(conn, as_of),
        lambda: _insight_subscription_total(conn, as_of),
        lambda: _insight_allocation_drift(conn, as_of),
        lambda: _insight_stale_data(conn, as_of),
        lambda: _insight_net_worth_trend(conn, as_of, nw),
        lambda: _insight_spending_over_pace(conn, as_of),
    ]

    insights: list[dict] = []
    for gen in generators:
        try:
            insights.extend(gen())
        except Exception:
            # A single failing generator must never crash the endpoint.
            pass
    return insights


def sync_insights(conn: sqlite3.Connection, insights: list[dict]) -> list[dict]:
    """Upsert generated insights into the DB and return the active set.

    Returns all rows where ``is_current = 1 AND dismissed_at IS NULL``,
    ordered by severity (alert first) then recency.
    """
    # Ensure table exists (self-healing if migration hasn't run yet).
    conn.execute(_CREATE_TABLE_SQL)

    existing: dict[str, dict] = {}
    for row in conn.execute(
        "SELECT id, insight_key, title, body, severity FROM insights"
    ):
        existing[row["insight_key"]] = dict(row)

    current_keys: set[str] = set()
    for ins in insights:
        key = ins["insight_key"]
        current_keys.add(key)

        if key in existing:
            ex = existing[key]
            if (
                ex["title"] != ins["title"]
                or ex["body"] != ins["body"]
                or ex["severity"] != ins["severity"]
            ):
                conn.execute(
                    "UPDATE insights SET title=?, body=?, severity=?, type=?, "
                    "source=?, updated_at=datetime('now'), is_current=1 "
                    "WHERE insight_key=?",
                    (ins["title"], ins["body"], ins["severity"],
                     ins["type"], ins["source"], key),
                )
            else:
                conn.execute(
                    "UPDATE insights SET is_current=1 WHERE insight_key=?",
                    (key,),
                )
        else:
            conn.execute(
                "INSERT INTO insights "
                "(insight_key, type, severity, title, body, source) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (key, ins["type"], ins["severity"],
                 ins["title"], ins["body"], ins["source"]),
            )

    # Conditions that no longer hold → mark stale.
    if current_keys:
        placeholders = ",".join("?" for _ in current_keys)
        conn.execute(
            f"UPDATE insights SET is_current=0 "
            f"WHERE insight_key NOT IN ({placeholders})",
            tuple(current_keys),
        )
    else:
        conn.execute("UPDATE insights SET is_current=0")

    conn.commit()

    rows = conn.execute(
        "SELECT id, insight_key, type, severity, title, body, source, "
        "       created_at, updated_at "
        "FROM insights "
        "WHERE is_current = 1 AND dismissed_at IS NULL "
        "ORDER BY "
        "  CASE severity "
        "    WHEN 'alert'    THEN 0 "
        "    WHEN 'warn'     THEN 1 "
        "    WHEN 'info'     THEN 2 "
        "    WHEN 'positive' THEN 3 "
        "  END, "
        "  updated_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Table DDL (used by sync_insights for self-healing)
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS insights (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_key  TEXT NOT NULL UNIQUE,
    type         TEXT NOT NULL,
    severity     TEXT NOT NULL CHECK (severity IN ('positive', 'info', 'warn', 'alert')),
    title        TEXT NOT NULL,
    body         TEXT NOT NULL,
    source       TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
    dismissed_at TEXT,
    is_current   INTEGER NOT NULL DEFAULT 1
)
"""


# ---------------------------------------------------------------------------
# Individual generators
# ---------------------------------------------------------------------------

def _insight_debt_interest(conn: sqlite3.Connection, as_of: date) -> list[dict]:
    """Flag each high-APR debt and its monthly interest cost."""
    debts = debt_roster(conn, as_of)
    out: list[dict] = []
    for d in debts:
        if d.apr is None or d.apr < HIGH_APR_THRESHOLD or d.balance <= 0:
            continue
        monthly = d.balance * (d.apr / 100.0 / 12.0)
        out.append({
            "insight_key": f"debt_interest:{d.name}",
            "type": "debt",
            "severity": "alert",
            "title": (
                f"{d.name} is costing you ~${monthly:,.0f}/month in interest"
            ),
            "body": (
                f"${d.balance:,.0f} balance at {d.apr:.1f}% APR — "
                f"~${monthly:,.0f}/month in interest, "
                f"${monthly * 12:,.0f}/year if the balance stays flat."
            ),
            "source": "debt_interest",
        })
    return out


def _insight_emergency_fund(md: dict) -> list[dict]:
    """Report emergency fund status relative to the 3-month target."""
    inputs = md.get("inputs", {})
    ef_months = inputs.get("emergency_fund_months")
    cash = inputs.get("liquid_cash", 0)
    monthly_avg = inputs.get("monthly_outflow_avg", 0)

    if ef_months is None or monthly_avg <= 0:
        return []

    if ef_months < 1:
        return [{
            "insight_key": "emergency_fund:critical",
            "type": "savings",
            "severity": "alert",
            "title": (
                f"Emergency fund covers only {ef_months:.1f} months of expenses"
            ),
            "body": (
                f"${cash:,.0f} in liquid cash against "
                f"${monthly_avg:,.0f}/month in expenses — "
                f"{ef_months:.1f} months of runway. Target: 3 months minimum."
            ),
            "source": "emergency_fund",
        }]

    if ef_months < 3:
        gap = (3 - ef_months) * monthly_avg
        return [{
            "insight_key": "emergency_fund:low",
            "type": "savings",
            "severity": "warn",
            "title": (
                f"Emergency fund is {ef_months:.1f} months — "
                f"${gap:,.0f} short of 3-month target"
            ),
            "body": (
                f"${cash:,.0f} in liquid cash covers {ef_months:.1f} months "
                f"of expenses. Another ${gap:,.0f} would reach the 3-month floor."
            ),
            "source": "emergency_fund",
        }]

    if ef_months >= 6:
        return [{
            "insight_key": "emergency_fund:strong",
            "type": "savings",
            "severity": "positive",
            "title": (
                f"Emergency fund is strong at {ef_months:.1f} months"
            ),
            "body": (
                f"${cash:,.0f} in liquid cash covers {ef_months:.1f} months — "
                f"well above the 3-6 month target."
            ),
            "source": "emergency_fund",
        }]

    return [{
        "insight_key": "emergency_fund:adequate",
        "type": "savings",
        "severity": "positive",
        "title": f"Emergency fund covers {ef_months:.1f} months of expenses",
        "body": (
            f"${cash:,.0f} in liquid cash covers {ef_months:.1f} months — "
            f"within the healthy 3-6 month range."
        ),
        "source": "emergency_fund",
    }]


def _insight_savings_rate(
    conn: sqlite3.Connection, as_of: date,
) -> list[dict]:
    """Compare the trailing 30-day savings rate to the 15% guideline."""
    start, end = parse_window("30d", today=as_of)
    sr = savings_rate(conn, start, end)
    rate = sr.get("rate")
    if rate is None:
        return []

    pct = rate * 100
    income, spent, saved = sr["income"], sr["spent"], sr["saved"]

    if pct < 0:
        return [{
            "insight_key": "savings_rate:negative",
            "type": "savings",
            "severity": "alert",
            "title": (
                f"Spending exceeds income ({pct:+.0f}% savings rate)"
            ),
            "body": (
                f"Last 30 days: ${income:,.0f} income vs. ${spent:,.0f} spent. "
                f"You're drawing down reserves by ${abs(saved):,.0f}."
            ),
            "source": "savings_rate",
        }]

    if pct < 10:
        return [{
            "insight_key": "savings_rate:low",
            "type": "savings",
            "severity": "warn",
            "title": (
                f"Savings rate is {pct:.0f}% — below the 15% guideline"
            ),
            "body": (
                f"Last 30 days: ${income:,.0f} income, ${spent:,.0f} spent, "
                f"${saved:,.0f} saved. The standard guideline is 15%+."
            ),
            "source": "savings_rate",
        }]

    if pct >= 20:
        return [{
            "insight_key": "savings_rate:strong",
            "type": "savings",
            "severity": "positive",
            "title": (
                f"Saving {pct:.0f}% of income — above the 15% target"
            ),
            "body": (
                f"Last 30 days: ${saved:,.0f} saved on ${income:,.0f} income."
            ),
            "source": "savings_rate",
        }]

    # 10-19%: decent, no insight needed.
    return []


def _insight_goals_pace(
    conn: sqlite3.Connection, as_of: date,
) -> list[dict]:
    """Flag goals that are behind pace."""
    goals = goal_progress(conn, as_of)
    out: list[dict] = []
    for g in goals:
        if g["status"] == "red":
            expected = g.get("expected_at_pace") or 0
            shortfall = expected - g["current"]
            parts = [f"Current: ${g['current']:,.0f}"]
            if expected:
                parts.append(f"vs. ${expected:,.0f} expected")
            if shortfall > 0:
                parts.append(f"(${shortfall:,.0f} behind)")
            if g.get("target_amount"):
                parts.append(f"Target: ${g['target_amount']:,.0f}")
            if g.get("target_date"):
                parts.append(f"by {g['target_date']}")
            out.append({
                "insight_key": f"goal_pace:{g['name']}:behind",
                "type": "goals",
                "severity": "warn",
                "title": f"'{g['name']}' is behind pace",
                "body": ". ".join(parts) + ".",
                "source": "goal_pace",
            })
        elif g["status"] == "yellow":
            out.append({
                "insight_key": f"goal_pace:{g['name']}:slightly_behind",
                "type": "goals",
                "severity": "info",
                "title": f"'{g['name']}' is slightly behind pace",
                "body": (
                    f"${g['current']:,.0f}"
                    + (f" / ${g['target_amount']:,.0f}" if g.get("target_amount") else "")
                    + " — close to on-track but needs a nudge."
                ),
                "source": "goal_pace",
            })
    return out


def _insight_goal_milestones(
    conn: sqlite3.Connection, as_of: date,
) -> list[dict]:
    """Celebrate goals that have passed 25/50/75% milestones."""
    goals = goal_progress(conn, as_of)
    out: list[dict] = []
    for g in goals:
        if g["status"] != "green" or not g.get("target_amount"):
            continue
        pct = (g["current"] / g["target_amount"] * 100) if g["target_amount"] > 0 else 0

        if pct >= 75:
            milestone = 75
        elif pct >= 50:
            milestone = 50
        elif pct >= 25:
            milestone = 25
        else:
            continue

        out.append({
            "insight_key": f"goal_milestone:{g['name']}:{milestone}",
            "type": "goals",
            "severity": "positive",
            "title": f"'{g['name']}' is {pct:.0f}% funded",
            "body": (
                f"${g['current']:,.0f} of ${g['target_amount']:,.0f} — on track"
                + (f" for {g['target_date']}" if g.get("target_date") else "")
                + "."
            ),
            "source": "goal_milestone",
        })
    return out


def _insight_subscription_total(
    conn: sqlite3.Connection, as_of: date,
) -> list[dict]:
    """Surface the total recurring/subscription spend if material."""
    recurring = detect_recurring(conn, as_of)
    if not recurring:
        return []

    total_monthly = sum(r["estimated_monthly"] for r in recurring)
    total_annual = sum(r["estimated_annual"] for r in recurring)
    count = len(recurring)

    if total_monthly < 50:
        return []

    top_3 = recurring[:3]
    top_list = ", ".join(
        f"{r['merchant']} (${r['estimated_monthly']:,.0f}/mo)" for r in top_3
    )
    return [{
        "insight_key": "subscriptions:total",
        "type": "spending",
        "severity": "info",
        "title": (
            f"{count} recurring charges totaling ${total_monthly:,.0f}/month"
        ),
        "body": (
            f"Detected subscriptions total ${total_monthly:,.0f}/month "
            f"(${total_annual:,.0f}/year). Largest: {top_list}."
        ),
        "source": "subscription_total",
    }]


def _insight_allocation_drift(
    conn: sqlite3.Connection, as_of: date,
) -> list[dict]:
    """Flag asset classes that are 5+ percentage points off target."""
    alloc = current_allocation(conn, as_of)
    targets = allocation_targets(conn, as_of)
    if not targets["targets"]:
        return []

    by_class = {item["asset_class"]: item["pct"] for item in alloc["by_class"]}
    out: list[dict] = []

    for asset_class, target_pct in targets["targets"].items():
        current_pct = by_class.get(asset_class, 0.0)
        drift = current_pct - target_pct
        if abs(drift) < 5:
            continue
        direction = "overweight" if drift > 0 else "underweight"
        label = asset_class.replace("_", " ").title()
        out.append({
            "insight_key": f"allocation_drift:{asset_class}",
            "type": "allocation",
            "severity": "warn" if abs(drift) >= 10 else "info",
            "title": f"{label} is {abs(drift):.0f}pp {direction}",
            "body": (
                f"Current: {current_pct:.1f}% vs. {target_pct:.1f}% target — "
                f"{abs(drift):.1f}pp {direction}."
            ),
            "source": "allocation_drift",
        })
    return out


def _insight_stale_data(
    conn: sqlite3.Connection, as_of: date,
) -> list[dict]:
    """Warn if no transactions have been imported recently."""
    row = conn.execute(
        "SELECT MAX(date) AS last_date FROM transactions"
    ).fetchone()

    if row is None or row["last_date"] is None:
        return [{
            "insight_key": "stale_data:no_transactions",
            "type": "data",
            "severity": "info",
            "title": "No transactions imported yet",
            "body": (
                "Import bank statements to get started: "
                "finance import <file> --account <name>."
            ),
            "source": "stale_data",
        }]

    last = date.fromisoformat(row["last_date"])
    days_old = (as_of - last).days

    if days_old >= 14:
        return [{
            "insight_key": "stale_data:old",
            "type": "data",
            "severity": "warn",
            "title": f"Transaction data is {days_old} days old",
            "body": (
                f"Most recent transaction: {row['last_date']}. "
                f"Run a sync or import fresh statements."
            ),
            "source": "stale_data",
        }]
    return []


def _insight_net_worth_trend(
    conn: sqlite3.Connection,
    as_of: date,
    nw_now: dict,
) -> list[dict]:
    """Month-over-month net worth change."""
    nw_prev = networth_at(conn, as_of - timedelta(days=30))
    current = nw_now["net_worth"]
    previous = nw_prev["net_worth"]

    if previous == 0 and current == 0:
        return []

    change = current - previous
    if abs(change) < 100:
        return []

    denom = abs(previous) if previous != 0 else abs(current)
    pct = (change / denom) * 100

    if change > 0:
        return [{
            "insight_key": "networth_trend:up",
            "type": "networth",
            "severity": "positive",
            "title": (
                f"Net worth up ${change:,.0f} ({pct:+.1f}%) over 30 days"
            ),
            "body": f"${previous:,.0f} -> ${current:,.0f}.",
            "source": "networth_trend",
        }]

    severity = "warn" if pct < -5 else "info"
    return [{
        "insight_key": "networth_trend:down",
        "type": "networth",
        "severity": severity,
        "title": (
            f"Net worth down ${abs(change):,.0f} ({pct:+.1f}%) over 30 days"
        ),
        "body": f"${previous:,.0f} -> ${current:,.0f}.",
        "source": "networth_trend",
    }]


def _insight_spending_over_pace(
    conn: sqlite3.Connection, as_of: date,
) -> list[dict]:
    """Flag categories where 30-day spending is well above the 3-month avg."""
    start, end = parse_window("30d", today=as_of)
    overpace = detect_category_over_pace(conn, start, end, multiplier=1.5)
    out: list[dict] = []
    for a in overpace[:3]:
        out.append({
            "insight_key": f"overspend:{a.subject}",
            "type": "spending",
            "severity": "warn",
            "title": f"{a.subject} spending is above your average",
            "body": a.detail,
            "source": "category_overspend",
        })
    return out
