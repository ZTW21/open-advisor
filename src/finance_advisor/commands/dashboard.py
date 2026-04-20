"""`finance dashboard` — launch the local web dashboard."""

from __future__ import annotations

import click

from finance_advisor.config import resolve_config
from finance_advisor.output import emit_error


@click.command("dashboard")
@click.option("--host", default="127.0.0.1", show_default=True,
              help="Bind address.")
@click.option("--port", default=8765, show_default=True, type=int,
              help="Bind port.")
@click.option("--no-browser", is_flag=True, default=False,
              help="Don't open a browser window on startup.")
@click.pass_context
def dashboard(ctx: click.Context, host: str, port: int, no_browser: bool) -> None:
    """Launch the local web dashboard."""
    try:
        import uvicorn  # noqa: F401
        from finance_advisor.web.server import create_app
    except ImportError:
        emit_error(
            ctx,
            "Web dashboard dependencies are not installed. "
            "Install them with: pip install open-advisor[web]",
            code="missing_deps",
        )
        return

    db_override = ctx.obj.get("db_override")
    app = create_app(db_override)

    if not no_browser:
        import threading
        import time
        import webbrowser

        def _open():
            time.sleep(1)
            webbrowser.open(f"http://{host}:{port}")

        threading.Thread(target=_open, daemon=True).start()

    click.echo(f"Dashboard running at http://{host}:{port}")
    click.echo("Press Ctrl+C to stop.")
    uvicorn.run(app, host=host, port=port, log_level="warning")
