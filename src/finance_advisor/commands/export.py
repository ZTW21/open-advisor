"""`finance export` — regenerate canonical JSON snapshots from the database.

Run this after any committed write. The `.sqlite` file is git-ignored, so
the JSON exports are what git actually tracks. Exports are deterministic:
same DB state = byte-identical JSON output.
"""

from __future__ import annotations

import click

from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect
from finance_advisor.exports import export_all
from finance_advisor.output import emit


@click.command("export")
@click.pass_context
def export(ctx: click.Context) -> None:
    """Regenerate all JSON exports in data/exports/."""
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    conn = connect(config.db_path)
    try:
        summary = export_all(conn, config.exports_dir)
    finally:
        conn.close()

    payload = {
        "ok": True,
        "exports_dir": str(config.exports_dir),
        "files": summary,
    }

    def _render(p: dict) -> None:
        click.echo(f"Wrote exports to: {p['exports_dir']}")
        files = p["files"]
        click.echo(f"  accounts:          {files['accounts']}")
        click.echo(f"  holdings:          {files['holdings']}")
        click.echo(f"  net_worth_history: {files['net_worth_history']}")
        tx_files = files["transactions"]
        if tx_files:
            click.echo(f"  transactions:      {len(tx_files)} monthly file(s)")
        else:
            click.echo("  transactions:      (none yet)")

    emit(ctx, payload, _render)
