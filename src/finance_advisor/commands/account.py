"""`finance account` — manage accounts (add, list, show).

Accounts are the canonical list of where money lives. Each account can be:
- checking, savings, credit_card, brokerage, retirement, loan, mortgage, other
- active or closed (closed accounts stay in the DB for history)

Narrative/metadata about each account lives in `accounts/<name>.md`.
The database holds the structured record and the balance history.
"""

from __future__ import annotations

import click

from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect, transaction
from finance_advisor.output import emit, emit_error


ACCOUNT_TYPES = (
    "checking",
    "savings",
    "credit_card",
    "brokerage",
    "retirement",
    "loan",
    "mortgage",
    "cash",
    "other",
)

ASSET_CLASSES = (
    "cash",
    "us_stocks",
    "intl_stocks",
    "bonds",
    "real_estate",
    "liability",
    "other",
)


@click.group("account")
def account() -> None:
    """Manage accounts."""


@account.command("add")
@click.option("--name", required=True, help="Short unique name (e.g., chase_checking).")
@click.option("--institution", required=True, help="Institution (e.g., Chase).")
@click.option(
    "--type",
    "account_type",
    required=True,
    type=click.Choice(ACCOUNT_TYPES),
    help="Account type.",
)
@click.option("--currency", default="USD", show_default=True, help="Currency code.")
@click.option("--opened-on", default=None, help="YYYY-MM-DD.")
@click.option("--notes", default=None, help="Freeform notes.")
@click.option(
    "--apr",
    default=None,
    type=float,
    help="Annual percentage rate (debt accounts). E.g., 24.99 for 24.99%.",
)
@click.option(
    "--min-payment",
    "min_payment",
    default=None,
    type=float,
    help="Minimum monthly payment (debt accounts).",
)
@click.option(
    "--asset-class",
    "asset_class",
    default=None,
    type=click.Choice(ASSET_CLASSES),
    help="Asset class (for rebalance). Defaults apply by account_type when unset.",
)
@click.option(
    "--expense-ratio",
    "expense_ratio_pct",
    default=None,
    type=float,
    help="Blended expense ratio as a percentage (e.g., 0.03 for 0.03%).",
)
@click.option(
    "--annual-fee",
    "annual_fee",
    default=None,
    type=float,
    help="Flat annual fee in account currency.",
)
@click.pass_context
def add(
    ctx: click.Context,
    name: str,
    institution: str,
    account_type: str,
    currency: str,
    opened_on: str | None,
    notes: str | None,
    apr: float | None,
    min_payment: float | None,
    asset_class: str | None,
    expense_ratio_pct: float | None,
    annual_fee: float | None,
) -> None:
    """Register a new account."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    conn = connect(config.db_path)
    try:
        existing = conn.execute(
            "SELECT id FROM accounts WHERE name = ?", (name,)
        ).fetchone()
        if existing is not None:
            emit_error(
                ctx,
                f"Account '{name}' already exists.",
                code="duplicate_account",
                details={"name": name},
            )
            return

        with transaction(conn):
            cur = conn.execute(
                "INSERT INTO accounts (name, institution, account_type, currency, "
                "active, opened_on, notes, apr, min_payment, asset_class, "
                "expense_ratio_pct, annual_fee) "
                "VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)",
                (
                    name,
                    institution,
                    account_type,
                    currency,
                    opened_on,
                    notes,
                    apr,
                    min_payment,
                    asset_class,
                    expense_ratio_pct,
                    annual_fee,
                ),
            )
            account_id = cur.lastrowid
    finally:
        conn.close()

    payload = {
        "ok": True,
        "account": {
            "id": account_id,
            "name": name,
            "institution": institution,
            "account_type": account_type,
            "currency": currency,
            "active": True,
            "opened_on": opened_on,
            "notes": notes,
            "apr": apr,
            "min_payment": min_payment,
            "asset_class": asset_class,
            "expense_ratio_pct": expense_ratio_pct,
            "annual_fee": annual_fee,
        },
    }

    def _render(p: dict) -> None:
        a = p["account"]
        extras: list[str] = []
        if a.get("apr") is not None:
            extras.append(f"apr={a['apr']}%")
        if a.get("min_payment") is not None:
            extras.append(f"min_pmt=${a['min_payment']}")
        if a.get("asset_class"):
            extras.append(f"asset_class={a['asset_class']}")
        if a.get("expense_ratio_pct") is not None:
            extras.append(f"er={a['expense_ratio_pct']}%")
        if a.get("annual_fee") is not None:
            extras.append(f"fee=${a['annual_fee']}")
        extra_str = f"  {' '.join(extras)}" if extras else ""
        click.echo(
            f"Added account: {a['name']} ({a['institution']} {a['account_type']}) [id={a['id']}]{extra_str}"
        )

    emit(ctx, payload, _render)


@account.command("list")
@click.option("--active-only", is_flag=True, default=False, help="Only show active accounts.")
@click.pass_context
def list_accounts(ctx: click.Context, active_only: bool) -> None:
    """List all accounts."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    conn = connect(config.db_path)
    try:
        query = (
            "SELECT id, name, institution, account_type, currency, active, "
            "opened_on, closed_on, notes "
            "FROM accounts"
        )
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY active DESC, name"
        rows = conn.execute(query).fetchall()
    finally:
        conn.close()

    accounts_list = [dict(r) for r in rows]
    # Convert int active to bool for JSON readability
    for a in accounts_list:
        a["active"] = bool(a["active"])

    payload = {"ok": True, "count": len(accounts_list), "accounts": accounts_list}

    def _render(p: dict) -> None:
        if not p["accounts"]:
            click.echo("No accounts registered. Use `finance account add` to add one.")
            return
        for a in p["accounts"]:
            status = "" if a["active"] else " [closed]"
            click.echo(f"  {a['name']}  ({a['institution']} {a['account_type']}){status}")
        click.echo(f"\nTotal: {p['count']}")

    emit(ctx, payload, _render)


@account.command("show")
@click.argument("name")
@click.pass_context
def show(ctx: click.Context, name: str) -> None:
    """Show details for a single account."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    conn = connect(config.db_path)
    try:
        row = conn.execute(
            "SELECT id, name, institution, account_type, currency, active, "
            "opened_on, closed_on, notes, apr, min_payment, asset_class, "
            "expense_ratio_pct, annual_fee, created_at, updated_at "
            "FROM accounts WHERE name = ?",
            (name,),
        ).fetchone()
        if row is None:
            emit_error(
                ctx,
                f"Account '{name}' not found.",
                code="account_not_found",
                details={"name": name},
            )
            return

        latest_balance = conn.execute(
            "SELECT as_of_date, balance, source FROM balance_history "
            "WHERE account_id = ? ORDER BY as_of_date DESC LIMIT 1",
            (row["id"],),
        ).fetchone()
    finally:
        conn.close()

    account_dict = dict(row)
    account_dict["active"] = bool(account_dict["active"])

    payload = {
        "ok": True,
        "account": account_dict,
        "latest_balance": dict(latest_balance) if latest_balance else None,
    }

    def _render(p: dict) -> None:
        a = p["account"]
        click.echo(f"Account: {a['name']}  (id={a['id']})")
        click.echo(f"  Institution: {a['institution']}")
        click.echo(f"  Type:        {a['account_type']}")
        click.echo(f"  Currency:    {a['currency']}")
        click.echo(f"  Active:      {a['active']}")
        if a["opened_on"]:
            click.echo(f"  Opened:      {a['opened_on']}")
        if a["closed_on"]:
            click.echo(f"  Closed:      {a['closed_on']}")
        if a["notes"]:
            click.echo(f"  Notes:       {a['notes']}")
        if a.get("apr") is not None:
            click.echo(f"  APR:         {a['apr']}%")
        if a.get("min_payment") is not None:
            click.echo(f"  Min payment: ${a['min_payment']}")
        if a.get("asset_class"):
            click.echo(f"  Asset class: {a['asset_class']}")
        if a.get("expense_ratio_pct") is not None:
            click.echo(f"  Expense ratio: {a['expense_ratio_pct']}%")
        if a.get("annual_fee") is not None:
            click.echo(f"  Annual fee: ${a['annual_fee']}")
        if p["latest_balance"]:
            b = p["latest_balance"]
            click.echo(f"  Latest balance: {b['balance']} as of {b['as_of_date']} (source: {b['source']})")
        else:
            click.echo("  Latest balance: (none recorded)")

    emit(ctx, payload, _render)


@account.command("edit")
@click.argument("name")
@click.option("--rename", default=None, help="New unique nickname.")
@click.option("--institution", default=None, help="Update institution.")
@click.option(
    "--type",
    "account_type",
    default=None,
    type=click.Choice(ACCOUNT_TYPES),
    help="Update account type.",
)
@click.option("--currency", default=None, help="Update currency code.")
@click.option("--opened-on", default=None, help="Set opened_on (YYYY-MM-DD).")
@click.option("--closed-on", default=None, help="Set closed_on (YYYY-MM-DD).")
@click.option("--notes", default=None, help="Replace notes.")
@click.option(
    "--active/--inactive",
    "active",
    default=None,
    help="Mark account active or inactive. Prefer `account close` for closing.",
)
@click.option(
    "--apr",
    default=None,
    type=float,
    help="Annual percentage rate (debt accounts).",
)
@click.option(
    "--min-payment",
    "min_payment",
    default=None,
    type=float,
    help="Minimum monthly payment (debt accounts).",
)
@click.option(
    "--asset-class",
    "asset_class",
    default=None,
    type=click.Choice(ASSET_CLASSES),
    help="Asset class (for rebalance).",
)
@click.option(
    "--expense-ratio",
    "expense_ratio_pct",
    default=None,
    type=float,
    help="Blended expense ratio as a percentage.",
)
@click.option(
    "--annual-fee",
    "annual_fee",
    default=None,
    type=float,
    help="Flat annual fee in account currency.",
)
@click.pass_context
def edit(
    ctx: click.Context,
    name: str,
    rename: str | None,
    institution: str | None,
    account_type: str | None,
    currency: str | None,
    opened_on: str | None,
    closed_on: str | None,
    notes: str | None,
    active: bool | None,
    apr: float | None,
    min_payment: float | None,
    asset_class: str | None,
    expense_ratio_pct: float | None,
    annual_fee: float | None,
) -> None:
    """Update metadata on an existing account. Only the flags you pass are changed."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    # Build the SET clause from only the flags the user provided.
    updates: list[tuple[str, object]] = []
    if rename is not None:
        updates.append(("name", rename))
    if institution is not None:
        updates.append(("institution", institution))
    if account_type is not None:
        updates.append(("account_type", account_type))
    if currency is not None:
        updates.append(("currency", currency))
    if opened_on is not None:
        updates.append(("opened_on", opened_on))
    if closed_on is not None:
        updates.append(("closed_on", closed_on))
    if notes is not None:
        updates.append(("notes", notes))
    if active is not None:
        updates.append(("active", 1 if active else 0))
    if apr is not None:
        updates.append(("apr", apr))
    if min_payment is not None:
        updates.append(("min_payment", min_payment))
    if asset_class is not None:
        updates.append(("asset_class", asset_class))
    if expense_ratio_pct is not None:
        updates.append(("expense_ratio_pct", expense_ratio_pct))
    if annual_fee is not None:
        updates.append(("annual_fee", annual_fee))

    if not updates:
        emit_error(
            ctx,
            "No fields to update. Pass at least one of --rename, --institution, --type, --currency, --opened-on, --closed-on, --notes, --active/--inactive, --apr, --min-payment, --asset-class, --expense-ratio, --annual-fee.",
            code="no_updates",
        )
        return

    conn = connect(config.db_path)
    try:
        current = conn.execute(
            "SELECT id, name, institution, account_type, currency, active, "
            "opened_on, closed_on, notes, apr, min_payment, asset_class, "
            "expense_ratio_pct, annual_fee "
            "FROM accounts WHERE name = ?",
            (name,),
        ).fetchone()
        if current is None:
            emit_error(
                ctx,
                f"Account '{name}' not found.",
                code="account_not_found",
                details={"name": name},
            )
            return

        # Guard: renaming to an already-taken name.
        if rename is not None and rename != name:
            conflict = conn.execute(
                "SELECT id FROM accounts WHERE name = ?", (rename,)
            ).fetchone()
            if conflict is not None:
                emit_error(
                    ctx,
                    f"Cannot rename to '{rename}' — another account already uses that name.",
                    code="duplicate_account",
                    details={"rename": rename},
                )
                return

        before = {k: current[k] for k in current.keys()}

        set_fragment = ", ".join(f"{col} = ?" for col, _ in updates)
        set_fragment += ", updated_at = datetime('now')"
        params = [val for _, val in updates]
        params.append(current["id"])

        with transaction(conn):
            conn.execute(
                f"UPDATE accounts SET {set_fragment} WHERE id = ?", params
            )

        after_row = conn.execute(
            "SELECT id, name, institution, account_type, currency, active, "
            "opened_on, closed_on, notes, apr, min_payment, asset_class, "
            "expense_ratio_pct, annual_fee "
            "FROM accounts WHERE id = ?",
            (current["id"],),
        ).fetchone()
    finally:
        conn.close()

    after = dict(after_row)
    after["active"] = bool(after["active"])
    before["active"] = bool(before["active"])

    changed = {k: {"before": before[k], "after": after[k]} for k in after if before[k] != after[k]}

    payload = {
        "ok": True,
        "account": after,
        "changed_fields": changed,
    }

    def _render(p: dict) -> None:
        a = p["account"]
        click.echo(f"Updated account: {a['name']}  (id={a['id']})")
        if not p["changed_fields"]:
            click.echo("  (no effective change)")
            return
        for field, diff in p["changed_fields"].items():
            click.echo(f"  {field}: {diff['before']!r} → {diff['after']!r}")

    emit(ctx, payload, _render)


@account.command("close")
@click.argument("name")
@click.option("--on", "closed_on", default=None, help="Date of closure (YYYY-MM-DD). Default: today.")
@click.pass_context
def close(ctx: click.Context, name: str, closed_on: str | None) -> None:
    """Mark an account as closed. Sets active=0 and stamps closed_on.

    Closed accounts stay in the DB for historical accuracy. Use `account edit
    --active` to reopen if closure was a mistake.
    """
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    if closed_on is None:
        from datetime import date

        closed_on = date.today().isoformat()

    conn = connect(config.db_path)
    try:
        row = conn.execute(
            "SELECT id, name, active, closed_on FROM accounts WHERE name = ?",
            (name,),
        ).fetchone()
        if row is None:
            emit_error(
                ctx,
                f"Account '{name}' not found.",
                code="account_not_found",
                details={"name": name},
            )
            return

        if not row["active"] and row["closed_on"]:
            payload = {
                "ok": True,
                "already_closed": True,
                "account": {"name": name, "closed_on": row["closed_on"]},
            }
            emit(
                ctx,
                payload,
                lambda p: click.echo(
                    f"Account '{name}' already closed on {p['account']['closed_on']}."
                ),
            )
            return

        with transaction(conn):
            conn.execute(
                "UPDATE accounts SET active = 0, closed_on = ?, "
                "updated_at = datetime('now') WHERE id = ?",
                (closed_on, row["id"]),
            )
    finally:
        conn.close()

    payload = {
        "ok": True,
        "already_closed": False,
        "account": {"name": name, "closed_on": closed_on},
    }

    def _render(p: dict) -> None:
        click.echo(f"Closed account '{p['account']['name']}' on {p['account']['closed_on']}.")

    emit(ctx, payload, _render)
