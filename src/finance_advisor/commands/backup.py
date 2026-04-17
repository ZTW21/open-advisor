"""`finance backup` — copy the SQLite DB to data/backups/<timestamp>.sqlite.

Run this before any destructive operation (schema change, bulk reimport).
Backups are local only; they are git-ignored alongside the live DB.
"""

from __future__ import annotations

import click

from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import backup
from finance_advisor.output import emit, emit_error


@click.command("backup")
@click.option("--tag", default="", help="Optional label appended to the filename.")
@click.pass_context
def backup_cmd(ctx: click.Context, tag: str) -> None:
    """Copy the database to data/backups/ with a timestamp."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    if not config.db_path.exists():
        emit_error(
            ctx,
            f"No database at {config.db_path}. Run `finance init` first.",
            code="db_not_found",
            details={"db_path": str(config.db_path)},
        )
        return

    out = backup(config.db_path, config.backups_dir, tag=tag)

    payload = {
        "ok": True,
        "backup_path": str(out),
        "source_db": str(config.db_path),
    }

    def _render(p: dict) -> None:
        click.echo(f"Backed up to: {p['backup_path']}")

    emit(ctx, payload, _render)
