"""Detect transfers between the user's own accounts.

A transfer is a paired outflow/inflow of the same absolute amount between
two accounts belonging to the user. We group paired transactions by setting
`transfer_group_id` on both to the same UUID.

Heuristic:
  - Opposite signs (one positive, one negative)
  - Same absolute amount (within 1 cent)
  - Dated within ±3 days of each other
  - On two different accounts
  - Neither already has a transfer_group_id

When multiple candidates exist for a given outflow, we pick the closest-dated
inflow. Unpaired transactions (cash transfers in/out of the system, or cases
where only one side was imported) stay un-grouped.

The import command calls `pair_transfers(conn)` on every commit. It's safe
to re-run — it only pairs currently-unpaired rows.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date

from finance_advisor.db import transaction


TRANSFER_WINDOW_DAYS = 3


def _days_between(d1: str, d2: str) -> int:
    return abs((date.fromisoformat(d1) - date.fromisoformat(d2)).days)


def pair_transfers(conn: sqlite3.Connection) -> int:
    """Scan currently-unpaired transactions and group opposite-sign matches.

    Returns the number of pairs created. Pure bookkeeping: category and amount
    stay untouched; only `transfer_group_id` is assigned.
    """
    # Only consider transactions not already in a group.
    rows = conn.execute(
        "SELECT id, account_id, date, amount FROM transactions "
        "WHERE transfer_group_id IS NULL ORDER BY date, id"
    ).fetchall()

    by_id = {r["id"]: {"account_id": r["account_id"], "date": r["date"], "amount": r["amount"]}
             for r in rows}

    # Greedy pairing: iterate outflows (amount < 0), find the best candidate
    # inflow with amount ≈ -this.amount on a different account within window.
    paired: dict[int, str] = {}
    used: set[int] = set()

    outflows = sorted(
        [rid for rid, r in by_id.items() if r["amount"] < 0],
        key=lambda rid: by_id[rid]["date"],
    )

    for out_id in outflows:
        if out_id in used:
            continue
        out = by_id[out_id]
        best: tuple[int, int] | None = None  # (days_delta, candidate_id)
        for in_id, in_row in by_id.items():
            if in_id in used or in_id == out_id:
                continue
            if in_row["account_id"] == out["account_id"]:
                continue
            if in_row["amount"] <= 0:
                continue
            if abs(in_row["amount"] + out["amount"]) > 0.005:
                continue
            delta = _days_between(in_row["date"], out["date"])
            if delta > TRANSFER_WINDOW_DAYS:
                continue
            if best is None or delta < best[0]:
                best = (delta, in_id)
        if best is not None:
            group = str(uuid.uuid4())
            paired[out_id] = group
            paired[best[1]] = group
            used.add(out_id)
            used.add(best[1])

    if not paired:
        return 0

    with transaction(conn):
        for txn_id, group in paired.items():
            conn.execute(
                "UPDATE transactions SET transfer_group_id = ? WHERE id = ?",
                (group, txn_id),
            )

    # Return number of pairs, not rows updated.
    return len(paired) // 2
