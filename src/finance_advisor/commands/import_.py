"""`finance import` — ingest CSV/OFX/QFX statements into the database.

Contract:

  1. Dry-run is the default. You must pass `--commit` to actually write.
     This is a hard rule (CLAUDE.md §5: no DB writes without preview +
     explicit confirmation).
  2. Importing the same file twice is a no-op: every transaction gets a
     stable `dedup_key = sha256(account_id|iso_date|amount|normalized_desc)`
     and the UNIQUE constraint in `transactions` rejects re-inserts.
  3. On commit we: create an `imports` audit row, INSERT transactions,
     run auto-categorization, run transfer pairing, and (if `--move` was
     set) move the source file into `transactions/processed/<YYYY>/`.
  4. On dry-run we report the summary but write nothing.
"""

from __future__ import annotations

import datetime
import hashlib
import shutil
from pathlib import Path
from typing import Optional

import click

from finance_advisor.categorize_engine import classify, load_rules
from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect, transaction
from finance_advisor.importers import ParseError, detect_format, parse_csv, parse_ofx
from finance_advisor.importers.base import ParsedRow
from finance_advisor.normalize import compute_dedup_key, normalize_merchant, parse_date
from finance_advisor.output import emit, emit_error
from finance_advisor.transfers import pair_transfers


PREVIEW_ROWS = 10


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _dispatch_parser(path: Path, fmt: str) -> list[ParsedRow]:
    if fmt == "csv":
        return parse_csv(path)
    if fmt in ("ofx", "qfx"):
        return parse_ofx(path)
    raise ParseError(f"unsupported format: {fmt}")


def _prepare_rows(account_id: int, raw_rows: list[ParsedRow]) -> list[dict]:
    """Normalize dates, compute merchant + dedup_key. Pure function."""
    prepared = []
    for r in raw_rows:
        iso_date = parse_date(r.date_raw)
        merchant = normalize_merchant(r.description)
        key = compute_dedup_key(account_id, iso_date, r.amount, merchant)
        prepared.append({
            "source_line": r.source_line,
            "account_id": account_id,
            "date": iso_date,
            "amount": r.amount,
            "merchant_normalized": merchant,
            "description_raw": r.description,
            "dedup_key": key,
        })
    return prepared


def _split_new_vs_dup(conn, prepared: list[dict]) -> tuple[list[dict], list[dict]]:
    """Partition rows into (new, duplicate) based on existing dedup_keys in DB."""
    if not prepared:
        return [], []
    keys = [p["dedup_key"] for p in prepared]
    existing: set[str] = set()
    CHUNK = 500
    for i in range(0, len(keys), CHUNK):
        chunk = keys[i:i + CHUNK]
        placeholders = ",".join("?" * len(chunk))
        rows = conn.execute(
            f"SELECT dedup_key FROM transactions WHERE dedup_key IN ({placeholders})",
            chunk,
        ).fetchall()
        existing.update(r["dedup_key"] for r in rows)
    new_rows = [p for p in prepared if p["dedup_key"] not in existing]
    dup_rows = [p for p in prepared if p["dedup_key"] in existing]
    return new_rows, dup_rows


def _classify_rows(conn, account_name: str, prepared: list[dict]) -> None:
    """Mutate each row dict to add category_id and matched_rule_id."""
    rules = load_rules(conn)
    for row in prepared:
        if rules:
            hit = classify(
                rules,
                account_name=account_name,
                normalized_desc=row["merchant_normalized"],
                amount=row["amount"],
            )
            row["category_id"] = hit[0] if hit else None
            row["matched_rule_id"] = hit[1] if hit else None
        else:
            row["category_id"] = None
            row["matched_rule_id"] = None


def _move_to_processed(path: Path, finance_dir: Path) -> Path:
    """Move the source file into transactions/processed/<YYYY>/.

    Year is derived from the file's mtime so historical imports group under
    the year the statement came from, not today's year.
    """
    year = datetime.datetime.fromtimestamp(path.stat().st_mtime).year
    year_dir = finance_dir / "transactions" / "processed" / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    dest = year_dir / path.name
    # Avoid clobbering: if a file by this name already exists, append `.N`.
    i = 1
    while dest.exists():
        dest = year_dir / f"{path.stem}.{i}{path.suffix}"
        i += 1
    shutil.move(str(path), str(dest))
    return dest


@click.command("import")
@click.argument("path", type=click.Path(path_type=Path))
@click.option("--account", required=True, help="Account nickname to import into.")
@click.option(
    "--format",
    "fmt",
    default="auto",
    type=click.Choice(["csv", "ofx", "qfx", "auto"]),
    show_default=True,
    help="File format. 'auto' uses extension + content sniff.",
)
@click.option(
    "--commit",
    is_flag=True,
    default=False,
    help="Actually write to the DB. Without this, import is a dry-run preview.",
)
@click.option(
    "--move/--no-move",
    default=True,
    show_default=True,
    help="On commit, move the source file into transactions/processed/<YYYY>/.",
)
@click.option(
    "--notes",
    default=None,
    help="Freeform notes attached to this import batch.",
)
@click.pass_context
def import_cmd(
    ctx: click.Context,
    path: Path,
    account: str,
    fmt: str,
    commit: bool,
    move: bool,
    notes: Optional[str],
) -> None:
    """Import transactions from a CSV/OFX/QFX file.

    Dry-run by default. Pass --commit to write.
    """
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    if not path.exists():
        emit_error(
            ctx,
            f"File not found: {path}",
            code="file_not_found",
            details={"path": str(path)},
        )
        return

    # Resolve format.
    if fmt == "auto":
        try:
            fmt = detect_format(path)
        except ValueError as exc:
            emit_error(
                ctx, str(exc), code="format_detection_failed",
                details={"path": str(path)},
            )
            return

    # Parse.
    try:
        raw_rows = _dispatch_parser(path, fmt)
    except ParseError as exc:
        emit_error(
            ctx, str(exc), code="parse_error",
            details={"path": str(path), "format": fmt},
        )
        return

    conn = connect(config.db_path)
    committed_import_id: Optional[int] = None
    moved_to: Optional[str] = None
    try:
        acct = conn.execute(
            "SELECT id, name FROM accounts WHERE name = ?", (account,)
        ).fetchone()
        if acct is None:
            emit_error(
                ctx,
                f"Account '{account}' not found.",
                code="account_not_found",
                details={"name": account},
            )
            return

        prepared = _prepare_rows(acct["id"], raw_rows)
        new_rows, dup_rows = _split_new_vs_dup(conn, prepared)

        # Collapse intra-file duplicates: if the same dedup_key shows up
        # twice in a single file (legitimate bank export quirk), keep the
        # first and count the rest as duplicates.
        seen: set[str] = set()
        deduped_new = []
        intra_file_dups = []
        for r in new_rows:
            if r["dedup_key"] in seen:
                intra_file_dups.append(r)
            else:
                seen.add(r["dedup_key"])
                deduped_new.append(r)
        new_rows = deduped_new

        _classify_rows(conn, account, new_rows)
        uncategorized = [r for r in new_rows if r["category_id"] is None]
        categorized = [r for r in new_rows if r["category_id"] is not None]

        file_checksum = _sha256_of_file(path)

        summary = {
            "rows_parsed": len(raw_rows),
            "new": len(new_rows),
            "duplicates": len(dup_rows) + len(intra_file_dups),
            "duplicates_in_file": len(intra_file_dups),
            "duplicates_in_db": len(dup_rows),
            "uncategorized": len(uncategorized),
            "categorized": len(categorized),
            "transfers_paired": 0,
            "file_checksum": file_checksum,
        }

        preview = [
            {
                "date": r["date"],
                "amount": r["amount"],
                "description": r["description_raw"],
                "merchant_normalized": r["merchant_normalized"],
                "category_id": r["category_id"],
            }
            for r in new_rows[:PREVIEW_ROWS]
        ]

        if commit:
            with transaction(conn):
                cur = conn.execute(
                    "INSERT INTO imports (source_file, file_checksum, row_count, "
                    "new_count, dup_count, flagged_count, status) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'committed')",
                    (
                        str(path),
                        file_checksum,
                        len(raw_rows),
                        len(new_rows),
                        len(dup_rows) + len(intra_file_dups),
                        len(uncategorized),
                    ),
                )
                committed_import_id = cur.lastrowid

                for r in new_rows:
                    conn.execute(
                        "INSERT INTO transactions "
                        "(account_id, date, amount, merchant_normalized, "
                        " description_raw, category_id, import_batch_id, dedup_key) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            r["account_id"],
                            r["date"],
                            r["amount"],
                            r["merchant_normalized"],
                            r["description_raw"],
                            r["category_id"],
                            committed_import_id,
                            r["dedup_key"],
                        ),
                    )

            summary["transfers_paired"] = pair_transfers(conn)

            if move:
                try:
                    dest = _move_to_processed(path, config.finance_dir)
                    moved_to = str(dest)
                except OSError as exc:
                    summary.setdefault("warnings", []).append(
                        f"failed to move source file: {exc}"
                    )
    finally:
        conn.close()

    payload = {
        "ok": True,
        "dry_run": not commit,
        "file": str(path),
        "account": account,
        "format": fmt,
        "summary": summary,
        "preview": preview,
        "import_id": committed_import_id,
        "moved_to": moved_to,
        "notes": notes,
    }

    def _render(p: dict) -> None:
        s = p["summary"]
        banner = "DRY RUN" if p["dry_run"] else f"COMMITTED (import id={p['import_id']})"
        click.echo(f"[{banner}] {p['file']} → {p['account']} ({p['format']})")
        click.echo(
            f"  parsed {s['rows_parsed']} rows: "
            f"{s['new']} new, {s['duplicates']} duplicate "
            f"({s['duplicates_in_db']} already in DB, {s['duplicates_in_file']} in file)"
        )
        click.echo(
            f"  categorized {s['categorized']}, uncategorized {s['uncategorized']}"
        )
        if not p["dry_run"]:
            click.echo(f"  transfers paired: {s['transfers_paired']}")
            if p["moved_to"]:
                click.echo(f"  moved file to: {p['moved_to']}")
        if p["preview"]:
            click.echo("\n  preview:")
            for r in p["preview"]:
                desc = r["merchant_normalized"][:40]
                click.echo(
                    f"    {r['date']}  ${r['amount']:>10,.2f}  {desc}"
                )
        if p["dry_run"] and s["new"] > 0:
            click.echo("\n  → Re-run with --commit to apply.")

    emit(ctx, payload, _render)
