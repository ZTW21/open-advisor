"""`finance init` — create the database, run migrations, and hydrate user templates.

`finance init` is the one-stop setup command. It:

1. Creates the SQLite database (if missing) and runs any pending migrations.
2. Ensures the working directories (`data/`, `data/exports/`, `data/backups/`) exist.
3. Hydrates user-facing scaffolds from `templates/` into the finance directory —
   things like `STRATEGY.md`, `profile.md`, `rules.md`, `goals.md`,
   `principles.md`, the six `state/*.md` snapshots, and `memory/MEMORY.md`.

Hydration is **idempotent and non-destructive** — it never overwrites a file
that already exists. That's what makes it safe to re-run after a framework
upgrade to pick up newly-added templates without touching files the user has
already populated.

See UPGRADING.md for the upgrade workflow this enables.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import click

from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import apply_migrations, connect, current_schema_version
from finance_advisor.output import emit


def hydrate_templates(
    finance_dir: Path, templates_dir: Path | None = None
) -> tuple[list[str], list[str]]:
    """Copy scaffolds from `templates/` into the finance dir without overwriting.

    Returns `(hydrated, skipped)` where each list contains paths relative to
    `finance_dir`. A file is *hydrated* if it was copied into place; *skipped*
    if the destination already existed.

    If `templates/` is not present next to `CLAUDE.md`, both lists are empty
    and hydration is a silent no-op (this lets a user delete `templates/`
    once they're fully onboarded, if they want to).
    """
    templates_dir = templates_dir or (finance_dir / "templates")
    if not templates_dir.is_dir():
        return ([], [])

    hydrated: list[str] = []
    skipped: list[str] = []

    for src in sorted(templates_dir.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(templates_dir)
        dst = finance_dir / rel
        if dst.exists():
            skipped.append(str(rel))
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        hydrated.append(str(rel))

    return hydrated, skipped


@click.command("init")
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize the database and hydrate user templates.

    Idempotent: safe to run multiple times. After a framework upgrade, re-run
    `finance init` to pull in any newly-added templates — existing files are
    never overwritten.
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

    hydrated, skipped = hydrate_templates(config.finance_dir)

    payload = {
        "ok": True,
        "db_path": str(config.db_path),
        "finance_dir": str(config.finance_dir),
        "created": created,
        "schema_version": version,
        "migrations_applied": applied,
        "templates_hydrated": hydrated,
        "templates_skipped": skipped,
    }

    def _render(p: dict) -> None:
        if p["created"]:
            click.echo(f"Created database: {p['db_path']}")
        else:
            click.echo(f"Database already exists: {p['db_path']}")
        if p["migrations_applied"]:
            click.echo(f"Applied migrations: {p['migrations_applied']}")
        click.echo(f"Schema version: {p['schema_version']}")
        if p["templates_hydrated"]:
            click.echo(f"Hydrated {len(p['templates_hydrated'])} templates:")
            for path in p["templates_hydrated"]:
                click.echo(f"  + {path}")
        if p["templates_skipped"]:
            click.echo(
                f"Skipped {len(p['templates_skipped'])} existing files "
                "(non-destructive — use these as-is or edit in place)"
            )

    emit(ctx, payload, _render)
