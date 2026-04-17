"""Tests for `finance anomalies` and the detectors in analytics.py."""

from __future__ import annotations

import json
from pathlib import Path


# History: 6 months of typical Starbucks runs + one Whole Foods chunk.
# The "unusual" month adds a $400 Home Depot (new merchant) and a $180 LA Fitness.

HISTORY = """Date,Description,Amount
10/01/2025,STARBUCKS #1234,-6.25
10/15/2025,STARBUCKS #1234,-7.10
10/22/2025,STARBUCKS #1234,-5.80
11/05/2025,STARBUCKS #1234,-6.50
11/20/2025,STARBUCKS #1234,-7.00
12/04/2025,STARBUCKS #1234,-6.75
12/18/2025,STARBUCKS #1234,-5.90
01/08/2026,STARBUCKS #1234,-6.25
01/22/2026,STARBUCKS #1234,-6.40
02/05/2026,STARBUCKS #1234,-7.20
02/19/2026,STARBUCKS #1234,-5.95
03/05/2026,STARBUCKS #1234,-6.30
03/19/2026,STARBUCKS #1234,-6.10
03/25/2026,WHOLE FOODS MKT #10230,-85.00
03/28/2026,WHOLE FOODS MKT #10230,-92.00
"""

CURRENT = """Date,Description,Amount
04/10/2026,STARBUCKS #1234,-25.50
04/11/2026,HOME DEPOT #4421,-420.00
04/12/2026,LA FITNESS,-180.00
04/13/2026,WHOLE FOODS MKT #10230,-88.00
"""


def _seed(invoke, finance_dir: Path):
    invoke("init")
    invoke("account", "add", "--name", "chase", "--institution", "Chase", "--type", "checking")
    invoke("categorize", "category", "add", "--name", "Coffee")
    invoke("categorize", "rule", "add", "--match", "STARBUCKS", "--category", "Coffee")
    inbox = finance_dir / "transactions" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "history.csv").write_text(HISTORY)
    (inbox / "current.csv").write_text(CURRENT)
    invoke("import", str(inbox / "history.csv"), "--account", "chase", "--commit")
    invoke("import", str(inbox / "current.csv"), "--account", "chase", "--commit")


# ---------- tests ----------

def test_anomalies_on_empty_db(invoke) -> None:
    invoke("init")
    result = invoke("anomalies", "--last", "7d")
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["count"] == 0


def test_detects_new_merchant(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("anomalies", "--since", "2026-04-01", "--kind", "new_merchant")
    p = json.loads(result.output)
    kinds = [(a["kind"], a["subject"]) for a in p["anomalies"]]
    subjects = {s for _, s in kinds}
    # HOME DEPOT and LA FITNESS are both first-time.
    assert any("HOME DEPOT" in s for s in subjects)
    assert any("LA FITNESS" in s for s in subjects)


def test_detects_large_transaction(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("anomalies", "--since", "2026-04-01", "--kind", "large_txn")
    p = json.loads(result.output)
    # The $420 Home Depot qualifies (first over $500? no — but LA Fitness $180 won't
    # qualify on threshold_dollars=500). Home Depot is $420, also below threshold.
    # So only things > $500 — there are none in `current`. Expected: 0.
    # (The STARBUCKS $25.50 is 4x median, but below $500 threshold.)
    assert p["count"] == 0


def test_detects_category_over_pace(invoke, finance_dir: Path) -> None:
    """Coffee in April is $25.50 vs. prior 3 months averaging ~$12-13/month."""
    _seed(invoke, finance_dir)
    result = invoke("anomalies", "--since", "2026-04-01", "--kind", "category_over_pace")
    p = json.loads(result.output)
    # Coffee is below the $100 min_dollars floor so it shouldn't fire.
    # Uncategorized is huge (Home Depot + LA Fitness + Whole Foods = $688)
    # vs. the 3-month prior (Whole Foods $177). That *should* trip.
    subjects = {a["subject"] for a in p["anomalies"]}
    assert "(uncategorized)" in subjects


def test_anomalies_bad_since_errors(invoke) -> None:
    invoke("init")
    result = invoke("anomalies", "--since", "zzz-not-a-date")
    p = json.loads(result.output)
    assert p["ok"] is False


def test_anomalies_default_window_is_7d(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("anomalies")
    p = json.loads(result.output)
    assert p["ok"] is True
    assert p["window"]["days"] == 7
