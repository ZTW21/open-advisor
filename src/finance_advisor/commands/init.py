"""`finance init` — create the database and run migrations."""

from __future__ import annotations

import click

from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import apply_migrations, connect, current_schema_version
from finance_advisor.output import emit


@click.command("init")
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize the database in the current finance directory.

    Creates data/finance.sqlite (if missing) and runs any pending migrations.
    Idempotent: safe to run multiple times.
    """
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    created = not config.db_path.exists()
    conn = connect(config.db_path)
    try:
        applied = apply_migrations(conn)
        version = current_schema_version(conn)
    finally:
        conn.close()

    payload = {
        "ok": True,
        "db_path": str(config.db_path),
        "finance_dir": str(config.finance_dir),
        "created": created,
        "schema_version": version,
        "migrations_applied": applied,
    }

    def _render(p: dict) -> None:
        if p["created"]:
            click.echo(f"Created database: {p['db_path']}")
        else:
            click.echo(f"Database already exists: {p['db_path']}")
        if p["migrations_applied"]:
            click.echo(f"Applied migrations: {p['migrations_applied']}")
        click.echo(f"Schema version: {p['schema_version']}")

    emit(ctx, payload, _render)
