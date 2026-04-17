"""Shared output helpers for CLI commands.

Every command supports a --json flag (resolved globally on the root group).
This module centralizes the "print as JSON or print as text" decision so
commands stay readable.
"""

from __future__ import annotations

import json
from typing import Any

import click


def _pretty_fallback(payload: dict[str, Any]) -> None:
    """Human-readable fallback when a command didn't provide a renderer.

    Uses `rich` if available, otherwise a plain indented JSON dump. Rich is
    a nicety, not a requirement — the CLI must run without it.
    """
    try:
        from rich.console import Console  # local import: optional dependency

        Console().print_json(data=payload)
    except ImportError:
        click.echo(json.dumps(payload, indent=2, sort_keys=True, default=str))


def emit(ctx: click.Context, payload: dict[str, Any], human_renderer=None) -> None:
    """Emit a payload. If --json is set, dump JSON. Otherwise call human_renderer.

    If no human_renderer is provided, we fall back to a pretty JSON dump so the
    user still sees useful output.
    """
    if ctx.obj.get("json_output"):
        click.echo(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return
    if human_renderer is not None:
        human_renderer(payload)
        return
    _pretty_fallback(payload)


def emit_error(ctx: click.Context, message: str, code: str = "error", details: dict | None = None) -> None:
    """Emit a standard error payload. Exits with code 1."""
    payload = {
        "ok": False,
        "error": code,
        "message": message,
    }
    if details:
        payload["details"] = details
    if ctx.obj.get("json_output"):
        click.echo(json.dumps(payload, indent=2, sort_keys=True, default=str), err=True)
    else:
        click.echo(f"error: {message}", err=True)
    ctx.exit(1)


def not_yet_implemented(ctx: click.Context, command: str, phase: str) -> None:
    """Standard stub response for commands not yet implemented."""
    payload = {
        "ok": False,
        "error": "not_yet_implemented",
        "command": command,
        "implemented_in_phase": phase,
        "message": f"`{command}` is scaffolded but not implemented yet. Planned for {phase}.",
    }
    emit(ctx, payload)
