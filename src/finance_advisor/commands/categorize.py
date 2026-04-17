"""`finance categorize` — manage categories, rules, and classify transactions.

Subcommand tree:

    finance categorize list          — show transactions (default: uncategorized)
    finance categorize set           — assign a category to one transaction
    finance categorize run           — re-run rules over existing transactions
    finance categorize category add  — create a category
    finance categorize category list — list categories
    finance categorize rule add      — create a categorization rule
    finance categorize rule list     — list rules
    finance categorize rule remove   — delete a rule

The `run` subcommand is dry-run by default (it previews what would change
without writing). Pass --commit to apply.
"""

from __future__ import annotations

from typing import Optional

import click

from finance_advisor.categorize_engine import classify, load_rules
from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect, transaction
from finance_advisor.output import emit, emit_error


# ---------- group ----------

@click.group("categorize")
def categorize() -> None:
    """Manage categories, rules, and transaction categorization."""


# ---------- transactions: list / set / run ----------

@categorize.command("list")
@click.option("--uncategorized/--all", default=True, show_default=True,
              help="Show only uncategorized transactions (default), or all.")
@click.option("--account", default=None, help="Filter to one account.")
@click.option("--since", default=None, help="Only transactions on/after YYYY-MM-DD.")
@click.option("--limit", default=100, show_default=True, type=int,
              help="Max rows to return.")
@click.pass_context
def list_txns(ctx, uncategorized, account, since, limit):
    """List transactions — uncategorized by default."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    conn = connect(config.db_path)
    try:
        where: list[str] = []
        params: list[object] = []
        if uncategorized:
            where.append("t.category_id IS NULL")
        if account is not None:
            acct = conn.execute("SELECT id FROM accounts WHERE name = ?",
                                (account,)).fetchone()
            if acct is None:
                emit_error(ctx, f"Account '{account}' not found.",
                           code="account_not_found", details={"name": account})
                return
            where.append("t.account_id = ?")
            params.append(acct["id"])
        if since is not None:
            where.append("t.date >= ?")
            params.append(since)

        where_clause = (" WHERE " + " AND ".join(where)) if where else ""
        params.append(limit)

        rows = conn.execute(
            "SELECT t.id, t.date, t.amount, t.merchant_normalized, "
            "       t.description_raw, t.category_id, c.name AS category, "
            "       a.name AS account "
            "FROM transactions t "
            "JOIN accounts a ON a.id = t.account_id "
            "LEFT JOIN categories c ON c.id = t.category_id"
            + where_clause
            + " ORDER BY t.date DESC, t.id DESC LIMIT ?",
            params,
        ).fetchall()
    finally:
        conn.close()

    txns = [dict(r) for r in rows]
    payload = {
        "ok": True,
        "count": len(txns),
        "filters": {"uncategorized": uncategorized, "account": account,
                    "since": since, "limit": limit},
        "transactions": txns,
    }

    def _render(p: dict) -> None:
        if not p["transactions"]:
            label = "uncategorized" if p["filters"]["uncategorized"] else "matching"
            click.echo(f"No {label} transactions.")
            return
        for t in p["transactions"]:
            cat = t["category"] or "(uncategorized)"
            click.echo(
                f"  [{t['id']:>5}]  {t['date']}  ${t['amount']:>10,.2f}  "
                f"{t['merchant_normalized'][:35]:<35}  {cat}"
            )
        click.echo(f"\nShowing {p['count']} transactions.")

    emit(ctx, payload, _render)


@categorize.command("set")
@click.option("--txn", "txn_id", required=True, type=int, help="Transaction id.")
@click.option("--category", required=True, help="Category name.")
@click.pass_context
def set_txn_category(ctx, txn_id: int, category: str):
    """Assign a category to a single transaction."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    conn = connect(config.db_path)
    try:
        txn = conn.execute(
            "SELECT id, category_id FROM transactions WHERE id = ?",
            (txn_id,),
        ).fetchone()
        if txn is None:
            emit_error(ctx, f"Transaction id {txn_id} not found.",
                       code="transaction_not_found",
                       details={"txn_id": txn_id})
            return

        cat = conn.execute("SELECT id FROM categories WHERE name = ?",
                           (category,)).fetchone()
        if cat is None:
            emit_error(ctx, f"Category '{category}' not found. "
                            f"Create it with `finance categorize category add --name {category}`.",
                       code="category_not_found", details={"name": category})
            return

        with transaction(conn):
            conn.execute(
                "UPDATE transactions SET category_id = ? WHERE id = ?",
                (cat["id"], txn_id),
            )
    finally:
        conn.close()

    payload = {
        "ok": True,
        "txn_id": txn_id,
        "category": category,
        "previous_category_id": txn["category_id"],
    }
    emit(ctx, payload,
         lambda p: click.echo(f"Assigned txn {p['txn_id']} → {p['category']}"))


@categorize.command("run")
@click.option("--uncategorized-only/--all", default=True, show_default=True,
              help="Re-classify only uncategorized rows (default) or all.")
@click.option("--since", default=None, help="Only transactions on/after YYYY-MM-DD.")
@click.option("--commit", is_flag=True, default=False,
              help="Apply changes. Without this, run is a dry-run preview.")
@click.pass_context
def run_rules(ctx, uncategorized_only: bool, since: Optional[str], commit: bool):
    """Re-run rules over existing transactions. Dry-run by default."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    conn = connect(config.db_path)
    try:
        rules = load_rules(conn)
        if not rules:
            payload = {"ok": True, "dry_run": not commit, "rules": 0,
                       "considered": 0, "would_update": 0, "updated": 0,
                       "sample": []}
            emit(ctx, payload,
                 lambda p: click.echo(
                     "No categorization rules defined. "
                     "Add some with `finance categorize rule add`."))
            return

        where = []
        params: list[object] = []
        if uncategorized_only:
            where.append("t.category_id IS NULL")
        if since is not None:
            where.append("t.date >= ?")
            params.append(since)
        where_clause = (" WHERE " + " AND ".join(where)) if where else ""

        rows = conn.execute(
            "SELECT t.id, t.amount, t.merchant_normalized, a.name AS account, "
            "       t.category_id "
            "FROM transactions t JOIN accounts a ON a.id = t.account_id"
            + where_clause + " ORDER BY t.date DESC",
            params,
        ).fetchall()

        updates: list[tuple[int, int, int, int | None]] = []
        for r in rows:
            hit = classify(
                rules,
                account_name=r["account"],
                normalized_desc=r["merchant_normalized"] or "",
                amount=r["amount"],
            )
            if hit is None:
                continue
            new_cat, rule_id = hit
            if r["category_id"] == new_cat:
                continue
            updates.append((r["id"], new_cat, rule_id, r["category_id"]))

        if commit and updates:
            with transaction(conn):
                for txn_id, new_cat, _rule_id, _prev in updates:
                    conn.execute(
                        "UPDATE transactions SET category_id = ? WHERE id = ?",
                        (new_cat, txn_id),
                    )
    finally:
        conn.close()

    payload = {
        "ok": True,
        "dry_run": not commit,
        "rules": len(rules),
        "considered": len(rows),
        "would_update": len(updates),
        "updated": len(updates) if commit else 0,
        "sample": [
            {"txn_id": tid, "new_category_id": nc, "rule_id": rid,
             "previous_category_id": prev}
            for tid, nc, rid, prev in updates[:20]
        ],
    }

    def _render(p: dict) -> None:
        banner = "DRY RUN" if p["dry_run"] else "COMMITTED"
        click.echo(f"[{banner}] {p['rules']} rules vs. {p['considered']} txns "
                   f"→ {p['would_update']} would change")
        if p["dry_run"] and p["would_update"]:
            click.echo("  → Re-run with --commit to apply.")

    emit(ctx, payload, _render)


# ---------- categories: add / list ----------

@categorize.group("category")
def category_group() -> None:
    """Manage categories."""


@category_group.command("add")
@click.option("--name", required=True)
@click.option("--parent", default=None, help="Parent category name (for subcategories).")
@click.option("--is-income", is_flag=True, default=False)
@click.option("--is-transfer", is_flag=True, default=False)
@click.pass_context
def cat_add(ctx, name: str, parent: Optional[str], is_income: bool, is_transfer: bool):
    """Add a category."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    conn = connect(config.db_path)
    try:
        existing = conn.execute("SELECT id FROM categories WHERE name = ?",
                                (name,)).fetchone()
        if existing is not None:
            emit_error(ctx, f"Category '{name}' already exists.",
                       code="duplicate_category", details={"name": name})
            return

        parent_id = None
        if parent is not None:
            p = conn.execute("SELECT id FROM categories WHERE name = ?",
                             (parent,)).fetchone()
            if p is None:
                emit_error(ctx, f"Parent category '{parent}' not found.",
                           code="parent_not_found", details={"parent": parent})
                return
            parent_id = p["id"]

        with transaction(conn):
            cur = conn.execute(
                "INSERT INTO categories (name, parent_id, is_income, is_transfer) "
                "VALUES (?, ?, ?, ?)",
                (name, parent_id, 1 if is_income else 0, 1 if is_transfer else 0),
            )
            new_id = cur.lastrowid
    finally:
        conn.close()

    payload = {
        "ok": True,
        "category": {
            "id": new_id, "name": name, "parent": parent,
            "is_income": is_income, "is_transfer": is_transfer,
        },
    }
    emit(ctx, payload,
         lambda p: click.echo(f"Added category: {p['category']['name']} "
                              f"[id={p['category']['id']}]"))


@category_group.command("list")
@click.pass_context
def cat_list(ctx):
    """List all categories."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    conn = connect(config.db_path)
    try:
        rows = conn.execute(
            "SELECT c.id, c.name, p.name AS parent, c.is_income, c.is_transfer "
            "FROM categories c LEFT JOIN categories p ON p.id = c.parent_id "
            "ORDER BY c.name"
        ).fetchall()
    finally:
        conn.close()

    cats = [dict(r) for r in rows]
    for c in cats:
        c["is_income"] = bool(c["is_income"])
        c["is_transfer"] = bool(c["is_transfer"])

    payload = {"ok": True, "count": len(cats), "categories": cats}

    def _render(p: dict) -> None:
        if not p["categories"]:
            click.echo("No categories yet.")
            return
        for c in p["categories"]:
            flags = []
            if c["is_income"]:
                flags.append("income")
            if c["is_transfer"]:
                flags.append("transfer")
            flag_str = f"  [{', '.join(flags)}]" if flags else ""
            parent_str = f" (under {c['parent']})" if c["parent"] else ""
            click.echo(f"  {c['name']}{parent_str}{flag_str}")
        click.echo(f"\nTotal: {p['count']}")

    emit(ctx, payload, _render)


# ---------- rules: add / list / remove ----------

@categorize.group("rule")
def rule_group() -> None:
    """Manage categorization rules."""


@rule_group.command("add")
@click.option("--match", "match_pattern", required=True,
              help="Pattern to match against normalized description.")
@click.option("--category", required=True, help="Category to assign.")
@click.option("--match-type", default="substring", show_default=True,
              type=click.Choice(["substring", "regex", "exact"]))
@click.option("--account", "account_filter", default=None,
              help="Only apply to this account.")
@click.option("--amount-filter", default=None,
              help="Only apply if amount meets condition (e.g., '>0', '<-50').")
@click.option("--priority", type=int, default=100, show_default=True)
@click.pass_context
def rule_add(ctx, match_pattern, category, match_type, account_filter,
             amount_filter, priority):
    """Add a categorization rule."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    conn = connect(config.db_path)
    try:
        cat = conn.execute("SELECT id FROM categories WHERE name = ?",
                           (category,)).fetchone()
        if cat is None:
            emit_error(ctx, f"Category '{category}' not found.",
                       code="category_not_found", details={"name": category})
            return

        if account_filter is not None:
            acct = conn.execute("SELECT id FROM accounts WHERE name = ?",
                                (account_filter,)).fetchone()
            if acct is None:
                emit_error(ctx, f"Account '{account_filter}' not found.",
                           code="account_not_found",
                           details={"name": account_filter})
                return

        # Validate regex compiles if match_type=regex.
        if match_type == "regex":
            import re as _re
            try:
                _re.compile(match_pattern)
            except _re.error as exc:
                emit_error(ctx, f"Invalid regex: {exc}", code="invalid_regex",
                           details={"pattern": match_pattern})
                return

        with transaction(conn):
            cur = conn.execute(
                "INSERT INTO categorization_rules "
                "(match_pattern, match_type, category_id, account_filter, "
                " amount_filter, priority, user_defined) "
                "VALUES (?, ?, ?, ?, ?, ?, 1)",
                (match_pattern, match_type, cat["id"], account_filter,
                 amount_filter, priority),
            )
            new_id = cur.lastrowid
    finally:
        conn.close()

    payload = {
        "ok": True,
        "rule": {
            "id": new_id, "match_pattern": match_pattern, "match_type": match_type,
            "category": category, "account_filter": account_filter,
            "amount_filter": amount_filter, "priority": priority,
        },
    }
    emit(ctx, payload,
         lambda p: click.echo(f"Added rule [{p['rule']['id']}] "
                              f"{p['rule']['match_pattern']!r} → {p['rule']['category']} "
                              f"(priority {p['rule']['priority']})"))


@rule_group.command("list")
@click.pass_context
def rule_list(ctx):
    """List all rules, highest priority first."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    conn = connect(config.db_path)
    try:
        rows = conn.execute(
            "SELECT r.id, r.match_pattern, r.match_type, r.priority, "
            "       c.name AS category, r.account_filter, r.amount_filter "
            "FROM categorization_rules r JOIN categories c ON c.id = r.category_id "
            "ORDER BY r.priority DESC, r.id ASC"
        ).fetchall()
    finally:
        conn.close()

    rules = [dict(r) for r in rows]
    payload = {"ok": True, "count": len(rules), "rules": rules}

    def _render(p: dict) -> None:
        if not p["rules"]:
            click.echo("No rules yet.")
            return
        for r in p["rules"]:
            filters = []
            if r["account_filter"]:
                filters.append(f"account={r['account_filter']}")
            if r["amount_filter"]:
                filters.append(f"amount{r['amount_filter']}")
            filt_str = f"  [{', '.join(filters)}]" if filters else ""
            click.echo(
                f"  [{r['id']:>3}] pri={r['priority']:>4}  "
                f"{r['match_type']:<9} {r['match_pattern']!r} → "
                f"{r['category']}{filt_str}"
            )
        click.echo(f"\nTotal: {p['count']}")

    emit(ctx, payload, _render)


@rule_group.command("remove")
@click.argument("rule_id", type=int)
@click.pass_context
def rule_remove(ctx, rule_id: int):
    """Delete a rule by id."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    conn = connect(config.db_path)
    try:
        row = conn.execute(
            "SELECT id, match_pattern FROM categorization_rules WHERE id = ?",
            (rule_id,),
        ).fetchone()
        if row is None:
            emit_error(ctx, f"Rule {rule_id} not found.",
                       code="rule_not_found", details={"rule_id": rule_id})
            return
        with transaction(conn):
            conn.execute("DELETE FROM categorization_rules WHERE id = ?",
                         (rule_id,))
    finally:
        conn.close()

    payload = {"ok": True, "removed_id": rule_id, "match_pattern": row["match_pattern"]}
    emit(ctx, payload,
         lambda p: click.echo(f"Removed rule {p['removed_id']} "
                              f"({p['match_pattern']!r})"))
