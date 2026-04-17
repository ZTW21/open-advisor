"""End-to-end tests for the import pipeline.

Phase 5 success criterion: dropping three overlapping months of statements
into `inbox/` produces a clean, deduped, categorized DB.

These tests exercise the full path: parse → normalize → dedup → categorize →
commit → transfer pair → move file.
"""

from __future__ import annotations

import json
from pathlib import Path


# ---------- fixtures (inline — plain CSVs to avoid a fixtures dir) ----------

CHASE_JAN = """Transaction Date,Post Date,Description,Category,Type,Amount
01/03/2026,01/04/2026,WHOLE FOODS MKT #10230 NYC,Groceries,Sale,-87.45
01/05/2026,01/06/2026,STARBUCKS STORE #1234 NYC,Food,Sale,-6.25
01/10/2026,01/11/2026,WHOLEFDS WC #10230,Groceries,Sale,-52.10
01/15/2026,01/16/2026,PAYROLL DEPOSIT ACME INC,Payment,Payment,3200.00
01/20/2026,01/21/2026,ATM WITHDRAWAL,Cash,Withdrawal,-200.00
"""

CHASE_JAN_FEB_OVERLAP = """Transaction Date,Post Date,Description,Category,Type,Amount
01/15/2026,01/16/2026,PAYROLL DEPOSIT ACME INC,Payment,Payment,3200.00
01/20/2026,01/21/2026,ATM WITHDRAWAL,Cash,Withdrawal,-200.00
02/01/2026,02/02/2026,RENT PAYMENT,Bills,Sale,-1800.00
02/05/2026,02/06/2026,WHOLE FOODS MKT #10230 NYC,Groceries,Sale,-45.32
02/10/2026,02/11/2026,NETFLIX.COM,Subscriptions,Sale,-15.99
"""

CHASE_FEB = """Transaction Date,Post Date,Description,Category,Type,Amount
02/01/2026,02/02/2026,RENT PAYMENT,Bills,Sale,-1800.00
02/05/2026,02/06/2026,WHOLE FOODS MKT #10230 NYC,Groceries,Sale,-45.32
02/10/2026,02/11/2026,NETFLIX.COM,Subscriptions,Sale,-15.99
02/15/2026,02/16/2026,PAYROLL DEPOSIT ACME INC,Payment,Payment,3200.00
02/28/2026,02/28/2026,TRANSFER TO ALLY SAVINGS,Transfer,Payment,-500.00
"""

ALLY_FEB = """Date,Description,Amount
02/28/2026,TRANSFER FROM CHASE CHECKING,500.00
02/28/2026,INTEREST EARNED,3.21
"""


# ---------- helpers ----------

def _seed(invoke, finance_dir: Path) -> Path:
    """Initialize DB + two accounts; return the inbox path."""
    invoke("init")
    invoke("account", "add", "--name", "chase", "--institution", "Chase", "--type", "checking")
    invoke("account", "add", "--name", "ally", "--institution", "Ally", "--type", "savings")
    inbox = finance_dir / "transactions" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    return inbox


def _write_inbox(inbox: Path, name: str, content: str) -> Path:
    p = inbox / name
    p.write_text(content)
    return p


# ---------- tests ----------

def test_import_dry_run_writes_nothing(invoke, finance_dir: Path) -> None:
    """Dry-run (default) reports what would happen but writes no rows."""
    inbox = _seed(invoke, finance_dir)
    csv_path = _write_inbox(inbox, "chase_jan.csv", CHASE_JAN)

    result = invoke("import", str(csv_path), "--account", "chase")
    assert result.exit_code == 0, result.output
    p = json.loads(result.output)
    assert p["dry_run"] is True
    assert p["summary"]["new"] == 5
    # File is still in inbox — not moved.
    assert csv_path.exists()

    # No transactions in DB.
    list_result = invoke("categorize", "list", "--all", "--limit", "999")
    assert json.loads(list_result.output)["count"] == 0


def test_import_commit_writes_rows_and_moves_file(invoke, finance_dir: Path) -> None:
    """--commit inserts rows and moves the file into processed/<YYYY>/."""
    inbox = _seed(invoke, finance_dir)
    csv_path = _write_inbox(inbox, "chase_jan.csv", CHASE_JAN)

    result = invoke("import", str(csv_path), "--account", "chase", "--commit")
    assert result.exit_code == 0, result.output
    p = json.loads(result.output)
    assert p["dry_run"] is False
    assert p["summary"]["new"] == 5
    assert p["import_id"] is not None
    assert p["moved_to"] is not None
    assert not csv_path.exists()
    assert Path(p["moved_to"]).exists()
    assert "processed" in p["moved_to"]

    # 5 transactions now in DB.
    listed = invoke("categorize", "list", "--all", "--limit", "999")
    assert json.loads(listed.output)["count"] == 5


def test_overlapping_imports_dedup_correctly(invoke, finance_dir: Path) -> None:
    """Three overlapping files → 10 unique rows (not 15). Phase 5 success criterion."""
    inbox = _seed(invoke, finance_dir)

    # Import three overlapping statements sequentially.
    jan = _write_inbox(inbox, "chase_jan.csv", CHASE_JAN)
    r1 = invoke("import", str(jan), "--account", "chase", "--commit")
    assert json.loads(r1.output)["summary"]["new"] == 5

    janfeb = _write_inbox(inbox, "chase_janfeb.csv", CHASE_JAN_FEB_OVERLAP)
    r2 = invoke("import", str(janfeb), "--account", "chase", "--commit")
    s2 = json.loads(r2.output)["summary"]
    assert s2["new"] == 3, s2
    assert s2["duplicates_in_db"] == 2, s2

    feb = _write_inbox(inbox, "chase_feb.csv", CHASE_FEB)
    r3 = invoke("import", str(feb), "--account", "chase", "--commit")
    s3 = json.loads(r3.output)["summary"]
    assert s3["new"] == 2, s3
    assert s3["duplicates_in_db"] == 3, s3

    # Total in DB = 5 + 3 + 2 = 10 unique.
    listed = invoke("categorize", "list", "--all", "--limit", "999")
    assert json.loads(listed.output)["count"] == 10


def test_reimport_is_noop(invoke, finance_dir: Path) -> None:
    """Re-importing the exact same file produces zero new rows."""
    inbox = _seed(invoke, finance_dir)
    jan = _write_inbox(inbox, "chase_jan.csv", CHASE_JAN)
    invoke("import", str(jan), "--account", "chase", "--commit", "--no-move")

    # File is still in inbox because of --no-move.
    result = invoke("import", str(jan), "--account", "chase", "--commit", "--no-move")
    p = json.loads(result.output)
    assert p["summary"]["new"] == 0
    assert p["summary"]["duplicates_in_db"] == 5


def test_import_unknown_account_errors(invoke, finance_dir: Path) -> None:
    inbox = _seed(invoke, finance_dir)
    csv = _write_inbox(inbox, "x.csv", CHASE_JAN)
    result = invoke("import", str(csv), "--account", "ghost")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "account_not_found"


def test_import_missing_file_errors(invoke, finance_dir: Path) -> None:
    _seed(invoke, finance_dir)
    result = invoke("import", "/does/not/exist.csv", "--account", "chase")
    p = json.loads(result.output)
    assert p["ok"] is False
    assert p["error"] == "file_not_found"


def test_import_auto_categorizes_via_rules(invoke, finance_dir: Path) -> None:
    """Rules in place at import time auto-categorize new rows."""
    inbox = _seed(invoke, finance_dir)
    invoke("categorize", "category", "add", "--name", "Groceries")
    invoke("categorize", "category", "add", "--name", "Income", "--is-income")
    invoke("categorize", "rule", "add", "--match", "WHOLE FOODS", "--category", "Groceries")
    invoke("categorize", "rule", "add", "--match", "WHOLEFDS", "--category", "Groceries")
    invoke("categorize", "rule", "add", "--match", "PAYROLL", "--category", "Income")

    csv = _write_inbox(inbox, "chase_jan.csv", CHASE_JAN)
    result = invoke("import", str(csv), "--account", "chase", "--commit")
    s = json.loads(result.output)["summary"]
    # Two grocery rows + one payroll = 3 categorized, 2 uncategorized (Starbucks + ATM).
    assert s["categorized"] == 3, s
    assert s["uncategorized"] == 2, s


def test_import_pairs_transfers_across_accounts(invoke, finance_dir: Path) -> None:
    """Matching outflow + inflow on two accounts gets a shared transfer_group_id."""
    inbox = _seed(invoke, finance_dir)

    invoke("import", str(_write_inbox(inbox, "feb.csv", CHASE_FEB)),
           "--account", "chase", "--commit")
    result = invoke("import", str(_write_inbox(inbox, "ally.csv", ALLY_FEB)),
                    "--account", "ally", "--commit")
    p = json.loads(result.output)
    assert p["summary"]["transfers_paired"] == 1, p["summary"]


def test_categorize_run_assigns_retroactively(invoke, finance_dir: Path) -> None:
    """Transactions imported before rules existed get picked up by `categorize run`."""
    inbox = _seed(invoke, finance_dir)

    # Import first (no rules yet)
    invoke("import", str(_write_inbox(inbox, "jan.csv", CHASE_JAN)),
           "--account", "chase", "--commit")

    # Add rules after.
    invoke("categorize", "category", "add", "--name", "Groceries")
    invoke("categorize", "rule", "add", "--match", "WHOLE FOODS", "--category", "Groceries")
    invoke("categorize", "rule", "add", "--match", "WHOLEFDS", "--category", "Groceries")

    # Dry-run first — nothing should be updated.
    dr = invoke("categorize", "run")
    dr_p = json.loads(dr.output)
    assert dr_p["dry_run"] is True
    assert dr_p["would_update"] == 2  # two grocery rows

    # Commit.
    cm = invoke("categorize", "run", "--commit")
    cm_p = json.loads(cm.output)
    assert cm_p["updated"] == 2

    # Only 3 uncategorized left (Starbucks, ATM, Payroll — we didn't add those rules).
    left = invoke("categorize", "list")
    assert json.loads(left.output)["count"] == 3
