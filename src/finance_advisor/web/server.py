"""FastAPI application factory for the open-advisor dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from finance_advisor.web.routers import (
    accounts,
    afford,
    allocation,
    anomalies,
    budget,
    cashflow,
    categories,
    dashboard,
    debt,
    fees,
    goals,
    holdings,
    imports,
    insights,
    mode,
    networth,
    recurring,
    reports,
    taxpack,
    transactions,
)

STATIC_DIR = Path(__file__).parent / "static"


def create_app(db_override: str | None = None) -> FastAPI:
    """Build and return the FastAPI app.

    Call `deps.configure(db_override)` before requests start so the DB
    path is resolved once rather than on every request.
    """
    from finance_advisor.web.deps import configure

    configure(db_override)

    app = FastAPI(
        title="open-advisor dashboard",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url=None,
    )

    # --- API routers ---
    app.include_router(dashboard.router)
    app.include_router(networth.router)
    app.include_router(accounts.router)
    app.include_router(mode.router)
    app.include_router(anomalies.router)
    app.include_router(cashflow.router)
    app.include_router(transactions.router)
    app.include_router(budget.router)
    app.include_router(goals.router)
    app.include_router(debt.router)
    app.include_router(allocation.router)
    app.include_router(fees.router)
    app.include_router(holdings.router)
    app.include_router(recurring.router)
    app.include_router(categories.router)
    app.include_router(reports.router)
    app.include_router(taxpack.router)
    app.include_router(afford.router)
    app.include_router(imports.router)
    app.include_router(insights.router)

    # --- Static files (Vite build output) ---
    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app
