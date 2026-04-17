"""`finance report` — generate periodic report payloads.

Each subcommand returns a JSON payload the AI advisor uses to write the
narrative. The `--write` flag persists a markdown file in `reports/` using
the advisor's voice defaults; the AI can also take the JSON and compose the
prose itself (that's the usual path).

    finance report daily                      # yesterday
    finance report daily --date 2026-04-15
    finance report weekly                     # last complete ISO week
    finance report weekly --week 2026-w15
    finance report monthly --month 2026-03    # one-page recap
    finance report quarterly                  # stub — Phase 10
    finance report annual                     # stub — Phase 10
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import click

from finance_advisor.analytics import (
    all_anomalies,
    allocation_targets,
    anomaly_to_dict,
    bucket_to_dict,
    budget_vs_actual,
    cashflow_by,
    cashflow_totals,
    current_allocation,
    fee_audit,
    format_iso_week,
    format_quarter,
    goal_progress,
    networth_at,
    parse_iso_week,
    parse_month,
    parse_quarter,
    parse_year,
    prior_quarter,
    savings_rate,
    tax_pack,
)
from finance_advisor.config import ensure_data_dirs, resolve_config
from finance_advisor.db import connect
from finance_advisor.output import emit, emit_error


# ---------- group ----------

@click.group("report")
def report() -> None:
    """Generate periodic reports (daily, weekly, monthly, quarterly, annual)."""


# ---------- helpers ----------

def _parse_date_or_default(spec: str | None, default: date) -> date:
    if spec is None:
        return default
    try:
        return date.fromisoformat(spec)
    except ValueError as e:
        raise ValueError(f"Invalid date: {spec!r} (expected YYYY-MM-DD)") from e


def _write_report(reports_dir: Path, filename: str, body: str) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / filename
    out.write_text(body)
    return out


# ---------- daily ----------

@report.command("daily")
@click.option("--date", "date_spec", default=None,
              help="Date: YYYY-MM-DD. Default: yesterday.")
@click.option("--write/--no-write", default=False, show_default=True,
              help="Write the brief to reports/YYYY-MM-DD-daily.md")
@click.pass_context
def daily(ctx: click.Context, date_spec: str | None, write: bool) -> None:
    """One-sentence daily brief payload.

    Returns all the raw numbers and anomalies the advisor needs to write
    a single-sentence brief. The AI composes the sentence; this just
    surfaces the inputs.
    """
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    try:
        target = _parse_date_or_default(date_spec, date.today() - timedelta(days=1))
    except ValueError as e:
        emit_error(ctx, str(e), code="bad_date")
        return

    # Window: just the one day.
    start = target
    end = target

    conn = connect(config.db_path)
    try:
        totals = cashflow_totals(conn, start, end)
        buckets = cashflow_by(conn, start, end, by="merchant")
        anoms = all_anomalies(conn, start, end)
        # 7-day pace for context
        week_start = target - timedelta(days=6)
        week_totals = cashflow_totals(conn, week_start, target)
    finally:
        conn.close()

    payload = {
        "ok": True,
        "date": target.isoformat(),
        "totals": totals,
        "rolling_7d": {
            "start": week_start.isoformat(),
            "end": target.isoformat(),
            **week_totals,
        },
        "top_merchants_today": [bucket_to_dict(b) for b in buckets[:3]],
        "anomalies": [anomaly_to_dict(a) for a in anoms],
        "suggested_sentence": _suggest_daily_sentence(target, totals, anoms),
    }

    written = None
    if write:
        body = _render_daily_markdown(payload)
        written = _write_report(
            config.reports_dir,
            f"{target.isoformat()}-daily.md",
            body,
        )
        payload["written_to"] = str(written)

    def _render(p: dict) -> None:
        click.echo(f"Daily brief for {p['date']}:")
        click.echo(f"  {p['suggested_sentence']}")
        if p["anomalies"]:
            click.echo("\nFlags:")
            for a in p["anomalies"]:
                click.echo(f"  - {a['detail']}")
        if p.get("written_to"):
            click.echo(f"\nWritten to: {p['written_to']}")

    emit(ctx, payload, _render)


def _suggest_daily_sentence(d: date, totals: dict, anomalies: list) -> str:
    """A reasonable default sentence the AI can keep or rewrite.

    The AI is expected to override this with voice; this is a fallback.
    `anomalies` is a list of `Anomaly` dataclasses.
    """
    if totals["count"] == 0:
        return f"No activity on {d.isoformat()}."
    if anomalies:
        return (
            f"On {d.isoformat()}: net ${totals['net']:+,.2f} across "
            f"{totals['count']} txns — {anomalies[0].detail}"
        )
    return (
        f"On {d.isoformat()}: net ${totals['net']:+,.2f} across "
        f"{totals['count']} txns, nothing unusual."
    )


def _render_daily_markdown(p: dict) -> str:
    lines = [
        f"---",
        f"date: {p['date']}",
        f"type: daily-brief",
        f"generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"---",
        "",
        f"# Daily brief — {p['date']}",
        "",
        p["suggested_sentence"],
        "",
    ]
    if p["anomalies"]:
        lines.append("## Flags")
        lines.append("")
        for a in p["anomalies"]:
            lines.append(f"- **{a['kind']}** — {a['detail']}")
        lines.append("")
    return "\n".join(lines)


# ---------- weekly ----------

@report.command("weekly")
@click.option("--week", default=None,
              help="ISO week: YYYY-Www. Default: most recent complete week.")
@click.option("--write/--no-write", default=False, show_default=True,
              help="Write the summary to reports/YYYY-Www-weekly.md")
@click.pass_context
def weekly(ctx: click.Context, week: str | None, write: bool) -> None:
    """~150-word weekly summary payload.

    Returns totals, top-5 spending categories, biggest merchants, pace vs.
    the prior 4-week median, and any anomalies. The AI composes the prose.
    """
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    try:
        if week:
            start, end = parse_iso_week(week)
        else:
            # Default: the most recent complete ISO week (Mon–Sun ending before today).
            today = date.today()
            # find last Sunday
            days_since_sunday = (today.weekday() + 1) % 7  # Monday=0 → 1, Sunday=6 → 0
            last_sunday = today - timedelta(days=days_since_sunday or 7)
            start = last_sunday - timedelta(days=6)
            end = last_sunday
        week_label = format_iso_week(start)
    except ValueError as e:
        emit_error(ctx, str(e), code="bad_week")
        return

    conn = connect(config.db_path)
    try:
        totals = cashflow_totals(conn, start, end)
        by_cat = cashflow_by(conn, start, end, by="category")
        by_merchant = cashflow_by(conn, start, end, by="merchant")
        anoms = all_anomalies(conn, start, end)

        # Prior 4-week median for pace comparison
        prior_totals = []
        for i in range(1, 5):
            p_end = start - timedelta(days=1 + 7 * (i - 1))
            p_start = p_end - timedelta(days=6)
            prior_totals.append(cashflow_totals(conn, p_start, p_end)["outflow"])
    finally:
        conn.close()

    prior_median = sorted(prior_totals)[len(prior_totals) // 2] if prior_totals else 0.0
    pace_delta = totals["outflow"] - prior_median
    pace_pct = (pace_delta / prior_median * 100) if prior_median else None

    payload = {
        "ok": True,
        "week": week_label,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "totals": totals,
        "by_category": [bucket_to_dict(b) for b in by_cat[:5]],
        "by_merchant": [bucket_to_dict(b) for b in by_merchant[:5]],
        "pace": {
            "this_week_outflow": totals["outflow"],
            "prior_4wk_median_outflow": prior_median,
            "delta_dollars": pace_delta,
            "delta_pct": pace_pct,
        },
        "anomalies": [anomaly_to_dict(a) for a in anoms],
    }

    written = None
    if write:
        body = _render_weekly_markdown(payload)
        written = _write_report(
            config.reports_dir,
            f"{week_label}-weekly.md",
            body,
        )
        payload["written_to"] = str(written)

    def _render(p: dict) -> None:
        click.echo(f"Week {p['week']} ({p['start']} → {p['end']}):")
        t = p["totals"]
        click.echo(f"  Net cashflow: ${t['net']:+,.2f}  (in ${t['inflow']:,.2f} / out ${t['outflow']:,.2f})")
        pace = p["pace"]
        if pace["prior_4wk_median_outflow"] > 0:
            sign = "+" if pace["delta_dollars"] >= 0 else ""
            click.echo(
                f"  Pace vs. 4wk median: {sign}${pace['delta_dollars']:,.2f} "
                f"({sign}{pace['delta_pct']:.0f}%)"
            )
        if p["by_category"]:
            click.echo("\n  Top categories (outflow):")
            for b in p["by_category"]:
                click.echo(f"    {b['key'][:22]:<22}  ${b['outflow']:>9,.2f}")
        if p["anomalies"]:
            click.echo("\n  Flags:")
            for a in p["anomalies"][:3]:
                click.echo(f"    - {a['detail']}")
        if p.get("written_to"):
            click.echo(f"\nWritten to: {p['written_to']}")

    emit(ctx, payload, _render)


def _render_weekly_markdown(p: dict) -> str:
    t = p["totals"]
    pace = p["pace"]
    lines = [
        f"---",
        f"week: {p['week']}",
        f"start: {p['start']}",
        f"end: {p['end']}",
        f"type: weekly-summary",
        f"generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"---",
        "",
        f"# Weekly summary — {p['week']}",
        "",
        f"**Net cashflow:** ${t['net']:+,.2f} (in ${t['inflow']:,.2f} / out ${t['outflow']:,.2f})",
        "",
    ]
    if pace["prior_4wk_median_outflow"] > 0:
        sign = "+" if pace["delta_dollars"] >= 0 else ""
        lines.append(
            f"**Pace vs. 4wk median outflow:** {sign}${pace['delta_dollars']:,.2f} "
            f"({sign}{pace['delta_pct']:.0f}%)"
        )
        lines.append("")
    if p["by_category"]:
        lines.append("## Top categories")
        lines.append("")
        for b in p["by_category"]:
            lines.append(f"- **{b['key']}** — ${b['outflow']:,.2f} ({b['count']} txns)")
        lines.append("")
    if p["anomalies"]:
        lines.append("## Flags")
        lines.append("")
        for a in p["anomalies"]:
            lines.append(f"- **{a['kind']}** — {a['detail']}")
        lines.append("")
    return "\n".join(lines)


# ---------- monthly / quarterly / annual (stubs for later phases) ----------

@report.command("monthly")
@click.option("--month", default=None, help="Month: YYYY-MM. Default: last complete month.")
@click.option("--write/--no-write", default=False, show_default=True,
              help="Write the report to reports/YYYY-MM-monthly.md")
@click.pass_context
def monthly(ctx: click.Context, month: str | None, write: bool) -> None:
    """One-page monthly report.

    Returns everything the advisor needs for the monthly check-in:
      - totals (inflow, outflow, net)
      - savings rate
      - net worth at start and end of month, delta
      - by-category outflow
      - top 5 merchants
      - budget vs. actual for categories with budgets
      - goal progress with red/yellow/green
      - anomalies for the month
      - month-over-month comparison against the prior month

    Pass --write to persist `reports/YYYY-MM-monthly.md`. The written file
    uses a plain-language default; the AI advisor is expected to compose
    a richer version from the JSON payload.
    """
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    try:
        if month:
            start, end = parse_month(month)
            month_label = month
        else:
            # Default: last complete month (today is in April → default is 2026-03)
            today = date.today()
            if today.month == 1:
                year, mon = today.year - 1, 12
            else:
                year, mon = today.year, today.month - 1
            month_label = f"{year:04d}-{mon:02d}"
            start, end = parse_month(month_label)
    except ValueError as e:
        emit_error(ctx, str(e), code="bad_month")
        return

    # Prior month
    if start.month == 1:
        prior_year, prior_mon = start.year - 1, 12
    else:
        prior_year, prior_mon = start.year, start.month - 1
    prior_label = f"{prior_year:04d}-{prior_mon:02d}"
    prior_start, prior_end = parse_month(prior_label)

    conn = connect(config.db_path)
    try:
        totals = cashflow_totals(conn, start, end)
        by_cat = cashflow_by(conn, start, end, by="category")
        by_merchant = cashflow_by(conn, start, end, by="merchant")
        rate = savings_rate(conn, start, end)
        budgets = budget_vs_actual(conn, start, end)
        goals = goal_progress(conn, end)
        anoms = all_anomalies(conn, start, end)
        nw_start = networth_at(conn, start - timedelta(days=1))
        nw_end = networth_at(conn, end)
        prior_totals = cashflow_totals(conn, prior_start, prior_end)
    finally:
        conn.close()

    nw_delta = nw_end["net_worth"] - nw_start["net_worth"]
    nw_delta_pct = (
        (nw_delta / nw_start["net_worth"] * 100)
        if nw_start["net_worth"]
        else None
    )

    outflow_delta = totals["outflow"] - prior_totals["outflow"]
    outflow_delta_pct = (
        (outflow_delta / prior_totals["outflow"] * 100)
        if prior_totals["outflow"] > 0
        else None
    )

    actions = _suggest_monthly_actions(rate, budgets, goals, anoms)

    payload = {
        "ok": True,
        "month": month_label,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "totals": totals,
        "savings_rate": rate,
        "net_worth": {
            "beginning": nw_start["net_worth"],
            "beginning_as_of": nw_start["oldest_balance_as_of"],
            "ending": nw_end["net_worth"],
            "ending_as_of": nw_end["oldest_balance_as_of"],
            "delta": nw_delta,
            "delta_pct": nw_delta_pct,
        },
        "by_category": [bucket_to_dict(b) for b in by_cat[:10]],
        "by_merchant": [bucket_to_dict(b) for b in by_merchant[:5]],
        "budget_vs_actual": budgets,
        "goals": goals,
        "anomalies": [anomaly_to_dict(a) for a in anoms],
        "month_over_month": {
            "prior_month": prior_label,
            "prior_outflow": prior_totals["outflow"],
            "outflow_delta": outflow_delta,
            "outflow_delta_pct": outflow_delta_pct,
            "prior_net": prior_totals["net"],
        },
        "suggested_actions": actions,
    }

    written = None
    if write:
        body = _render_monthly_markdown(payload)
        written = _write_report(
            config.reports_dir,
            f"{month_label}-monthly.md",
            body,
        )
        payload["written_to"] = str(written)

    def _render(p: dict) -> None:
        click.echo(f"Monthly report — {p['month']}  ({p['start']} → {p['end']})")
        t = p["totals"]
        click.echo(f"  Cashflow:   in ${t['inflow']:>10,.2f}  out ${t['outflow']:>10,.2f}  net ${t['net']:>+10,.2f}")
        r = p["savings_rate"]
        if r["rate"] is not None:
            click.echo(f"  Savings:    ${r['saved']:,.2f} of ${r['income']:,.2f}  ({r['rate']*100:+.1f}%)")
        nw = p["net_worth"]
        sign = "+" if nw["delta"] >= 0 else ""
        click.echo(f"  Net worth:  ${nw['beginning']:,.2f} → ${nw['ending']:,.2f}  ({sign}${nw['delta']:,.2f})")
        mom = p["month_over_month"]
        click.echo(f"  vs {mom['prior_month']}: outflow {('+$' if mom['outflow_delta']>=0 else '-$')}{abs(mom['outflow_delta']):,.2f}")

        if p["budget_vs_actual"]:
            click.echo("\n  Budget vs. actual:")
            for b in p["budget_vs_actual"][:5]:
                bar = "OVER" if b["variance"] > 0 else "under"
                click.echo(
                    f"    {b['category'][:20]:<20}  planned ${b['planned']:>8,.2f}  "
                    f"actual ${b['actual']:>8,.2f}  {bar} ${abs(b['variance']):,.2f}"
                )

        if p["goals"]:
            click.echo("\n  Goals:")
            for g in p["goals"]:
                dot = {"green": "OK ", "yellow": "WATCH", "red": "BEHIND", "info": "   "}[g["status"]]
                if g["target_amount"]:
                    click.echo(
                        f"    [{dot}] {g['name']:<25} ${g['current']:,.2f} / ${g['target_amount']:,.2f}"
                    )
                else:
                    click.echo(f"    [{dot}] {g['name']:<25} ${g['current']:,.2f}")

        if p["suggested_actions"]:
            click.echo("\n  Suggested actions:")
            for i, a in enumerate(p["suggested_actions"], 1):
                click.echo(f"    {i}. {a}")

        if p.get("written_to"):
            click.echo(f"\nWritten to: {p['written_to']}")

    emit(ctx, payload, _render)


def _suggest_monthly_actions(
    rate: dict,
    budgets: list[dict],
    goals: list[dict],
    anomalies: list,
) -> list[str]:
    """Heuristic default actions — the AI rewrites with voice.

    We surface at most 3 signals, in priority order:
      1. Biggest category over-budget (actionable).
      2. Any red-status goal (needs attention).
      3. If savings rate is under 10% and income > 0, flag it.
      4. Otherwise pull the heaviest anomaly if we still have room.
    """
    out: list[str] = []
    worst_budget = next((b for b in budgets if b["variance"] > 0), None)
    if worst_budget:
        out.append(
            f"Dial in {worst_budget['category']} — you're ${worst_budget['variance']:,.2f} "
            f"over plan this month."
        )
    red_goal = next((g for g in goals if g["status"] == "red"), None)
    if red_goal and len(out) < 3:
        gap = None
        if red_goal["expected_at_pace"] is not None:
            gap = red_goal["expected_at_pace"] - red_goal["current"]
        if gap and gap > 0:
            out.append(
                f"Catch up on '{red_goal['name']}' — behind pace by ${gap:,.2f}."
            )
        else:
            out.append(f"Revisit '{red_goal['name']}' — target date passed or behind.")
    if rate["rate"] is not None and rate["rate"] < 0.10 and len(out) < 3:
        out.append(
            f"Savings rate is {rate['rate']*100:.1f}% this month — aim for 10%+. "
            f"Slack to find: ${rate['spent']:,.2f} spent on ${rate['income']:,.2f} income."
        )
    if len(out) < 3 and anomalies:
        top = anomalies[0]
        out.append(f"Review: {top.detail}")
    return out


def _render_monthly_markdown(p: dict) -> str:
    t = p["totals"]
    r = p["savings_rate"]
    nw = p["net_worth"]
    mom = p["month_over_month"]

    lines = [
        f"---",
        f"month: {p['month']}",
        f"start: {p['start']}",
        f"end: {p['end']}",
        f"type: monthly-report",
        f"generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"---",
        "",
        f"# Monthly report — {p['month']}",
        "",
        f"## Net worth",
        "",
        f"**${nw['beginning']:,.2f} → ${nw['ending']:,.2f}**  "
        f"({'+' if nw['delta']>=0 else ''}${nw['delta']:,.2f}"
        + (f", {nw['delta_pct']:+.2f}%" if nw['delta_pct'] is not None else "")
        + ")",
        "",
        f"## Cash flow",
        "",
        f"- Inflow: **${t['inflow']:,.2f}**",
        f"- Outflow: **${t['outflow']:,.2f}**",
        f"- Net: **${t['net']:+,.2f}**",
    ]
    if r["rate"] is not None:
        lines.append(
            f"- Savings rate: **{r['rate']*100:.1f}%** "
            f"(${r['saved']:,.2f} of ${r['income']:,.2f})"
        )
    if mom["outflow_delta_pct"] is not None:
        sign = "+" if mom["outflow_delta"] >= 0 else ""
        lines.append(
            f"- vs. {mom['prior_month']}: outflow {sign}${mom['outflow_delta']:,.2f} "
            f"({sign}{mom['outflow_delta_pct']:.1f}%)"
        )
    lines.append("")

    if p["by_category"]:
        lines.append("## Spending by category")
        lines.append("")
        for b in p["by_category"]:
            if b["outflow"] > 0:
                lines.append(f"- **{b['key']}** — ${b['outflow']:,.2f} ({b['count']} txns)")
        lines.append("")

    if p["budget_vs_actual"]:
        lines.append("## Budget vs. actual")
        lines.append("")
        for b in p["budget_vs_actual"]:
            marker = "⚠️ over" if b["variance"] > 0 else "on track"
            lines.append(
                f"- **{b['category']}** — planned ${b['planned']:,.2f}, "
                f"actual ${b['actual']:,.2f} ({marker} by ${abs(b['variance']):,.2f})"
            )
        lines.append("")

    if p["goals"]:
        lines.append("## Goals")
        lines.append("")
        dot = {"green": "🟢", "yellow": "🟡", "red": "🔴", "info": "⚪"}
        for g in p["goals"]:
            if g["target_amount"]:
                lines.append(
                    f"- {dot[g['status']]} **{g['name']}** — "
                    f"${g['current']:,.2f} / ${g['target_amount']:,.2f}"
                    + (f" (target: {g['target_date']})" if g['target_date'] else "")
                )
            else:
                lines.append(f"- {dot[g['status']]} **{g['name']}** — ${g['current']:,.2f}")
        lines.append("")

    if p["anomalies"]:
        lines.append("## Flags")
        lines.append("")
        for a in p["anomalies"][:5]:
            lines.append(f"- **{a['kind']}** — {a['detail']}")
        lines.append("")

    if p["suggested_actions"]:
        lines.append("## Suggested actions")
        lines.append("")
        for i, a in enumerate(p["suggested_actions"], 1):
            lines.append(f"{i}. {a}")
        lines.append("")

    return "\n".join(lines)


@report.command("quarterly")
@click.option("--quarter", default=None, help="Quarter: YYYY-Qn. Default: last complete quarter.")
@click.option("--write/--no-write", default=False, show_default=True,
              help="Write the review to reports/YYYY-Qn.md")
@click.option("--fee-threshold", default=0.25, show_default=True, type=float,
              help="Expense-ratio threshold (percent) for the fee audit.")
@click.pass_context
def quarterly(
    ctx: click.Context, quarter: str | None, write: bool, fee_threshold: float
) -> None:
    """~2-page quarterly review payload.

    Returns everything needed for the quarterly review:
      - totals (inflow, outflow, net, savings rate) for the quarter
      - net worth at quarter start and end
      - by-category and by-merchant outflow
      - goal progress at quarter end
      - allocation + drift
      - fee audit
      - quarter-over-quarter comparison
      - anomalies
      - suggested actions

    The AI composes the prose; --write persists a default markdown
    review to `reports/YYYY-Qn.md`.
    """
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    try:
        if quarter:
            start, end = parse_quarter(quarter)
            label = quarter.upper().replace("Q", "Q")  # canonicalize
            # Normalize formatting: "2026-q1" → "2026-Q1"
            label = f"{start.year:04d}-Q{(start.month - 1) // 3 + 1}"
        else:
            # Default: the most recent *complete* quarter (today is in April 2026
            # → default is 2026-Q1). If today is mid-quarter, use the prior one.
            today = date.today()
            current_q = (today.month - 1) // 3 + 1
            # Current quarter isn't complete until its last day passes.
            from calendar import monthrange
            last_month_of_q = 3 * current_q
            last_day_of_q = monthrange(today.year, last_month_of_q)[1]
            end_of_current_q = date(today.year, last_month_of_q, last_day_of_q)
            if today <= end_of_current_q:
                # Fall back to prior quarter
                if current_q == 1:
                    label = f"{today.year - 1:04d}-Q4"
                else:
                    label = f"{today.year:04d}-Q{current_q - 1}"
            else:
                label = f"{today.year:04d}-Q{current_q}"
            start, end = parse_quarter(label)
    except ValueError as e:
        emit_error(ctx, str(e), code="bad_quarter")
        return

    # Prior quarter
    prior_label = prior_quarter(label)
    prior_start, prior_end = parse_quarter(prior_label)

    conn = connect(config.db_path)
    try:
        totals = cashflow_totals(conn, start, end)
        prior_totals = cashflow_totals(conn, prior_start, prior_end)
        by_cat = cashflow_by(conn, start, end, by="category")
        by_merchant = cashflow_by(conn, start, end, by="merchant")
        rate = savings_rate(conn, start, end)
        goals = goal_progress(conn, end)
        anoms = all_anomalies(conn, start, end)
        nw_start = networth_at(conn, start - timedelta(days=1))
        nw_end = networth_at(conn, end)
        alloc = current_allocation(conn, end)
        targets_obj = allocation_targets(conn, end)
        fees_result = fee_audit(conn, end, threshold_pct=fee_threshold)
    finally:
        conn.close()

    nw_delta = nw_end["net_worth"] - nw_start["net_worth"]
    nw_delta_pct = (
        (nw_delta / nw_start["net_worth"] * 100) if nw_start["net_worth"] else None
    )
    outflow_delta = totals["outflow"] - prior_totals["outflow"]
    outflow_delta_pct = (
        (outflow_delta / prior_totals["outflow"] * 100)
        if prior_totals["outflow"] > 0 else None
    )

    # Build drift rows joining current allocation + targets at quarter end.
    targets_map = targets_obj["targets"]
    current_map = {c["asset_class"]: c for c in alloc["by_class"]}
    drift_rows: list[dict] = []
    for ac in sorted(set(current_map.keys()) | set(targets_map.keys())):
        cur_pct = current_map[ac]["pct"] if ac in current_map else 0.0
        tgt_pct = targets_map.get(ac)
        drift_rows.append({
            "asset_class": ac,
            "current_pct": cur_pct,
            "target_pct": tgt_pct,
            "drift_pp": (round(cur_pct - tgt_pct, 2) if tgt_pct is not None else None),
        })

    actions = _suggest_quarterly_actions(rate, goals, drift_rows, fees_result)

    payload = {
        "ok": True,
        "quarter": label,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "totals": totals,
        "savings_rate": rate,
        "net_worth": {
            "beginning": nw_start["net_worth"],
            "beginning_as_of": nw_start["oldest_balance_as_of"],
            "ending": nw_end["net_worth"],
            "ending_as_of": nw_end["oldest_balance_as_of"],
            "delta": nw_delta,
            "delta_pct": nw_delta_pct,
        },
        "by_category": [bucket_to_dict(b) for b in by_cat[:10]],
        "by_merchant": [bucket_to_dict(b) for b in by_merchant[:5]],
        "goals": goals,
        "allocation": {
            "assets_total": alloc["assets_total"],
            "by_class": alloc["by_class"],
            "targets": targets_map,
            "targets_set": bool(targets_map),
            "drift": drift_rows,
        },
        "fees": {
            "total_annual_cost": fees_result["total_annual_cost"],
            "threshold_pct": fees_result["threshold_pct"],
            "flagged": fees_result["flagged"],
            "accounts": fees_result["accounts"],
            "missing_fee_info": fees_result["missing_fee_info"],
        },
        "anomalies": [anomaly_to_dict(a) for a in anoms[:10]],
        "quarter_over_quarter": {
            "prior_quarter": prior_label,
            "prior_outflow": prior_totals["outflow"],
            "outflow_delta": outflow_delta,
            "outflow_delta_pct": outflow_delta_pct,
        },
        "suggested_actions": actions,
    }

    if write:
        body = _render_quarterly_markdown(payload)
        written = _write_report(config.reports_dir, f"{label}.md", body)
        payload["written_to"] = str(written)

    def _render(p: dict) -> None:
        click.echo(f"Quarterly review — {p['quarter']} ({p['start']} → {p['end']})")
        t = p["totals"]
        click.echo(
            f"  Cashflow:  in ${t['inflow']:>10,.2f}  out ${t['outflow']:>10,.2f}  "
            f"net ${t['net']:>+10,.2f}"
        )
        r = p["savings_rate"]
        if r["rate"] is not None:
            click.echo(
                f"  Savings:   ${r['saved']:,.2f} of ${r['income']:,.2f} "
                f"({r['rate']*100:+.1f}%)"
            )
        nw = p["net_worth"]
        sign = "+" if nw["delta"] >= 0 else ""
        click.echo(
            f"  Net worth: ${nw['beginning']:,.2f} → ${nw['ending']:,.2f}  "
            f"({sign}${nw['delta']:,.2f})"
        )
        qoq = p["quarter_over_quarter"]
        click.echo(
            f"  vs {qoq['prior_quarter']}: outflow "
            f"{'+$' if qoq['outflow_delta']>=0 else '-$'}"
            f"{abs(qoq['outflow_delta']):,.2f}"
        )

        if p["allocation"]["targets_set"]:
            click.echo("\n  Allocation drift:")
            for row in p["allocation"]["drift"]:
                tgt = (
                    f"{row['target_pct']:.1f}%" if row["target_pct"] is not None else "—"
                )
                drift = (
                    f"{row['drift_pp']:+.1f}pp" if row["drift_pp"] is not None else "—"
                )
                click.echo(
                    f"    {row['asset_class']:<13} cur {row['current_pct']:>5.1f}%  "
                    f"tgt {tgt:>6}  drift {drift:>7}"
                )
        if p["fees"]["flagged"]:
            click.echo("\n  Fee flags (above threshold):")
            for f in p["fees"]["flagged"]:
                click.echo(
                    f"    - {f['account']}: {f['expense_ratio_pct']:.3f}% "
                    f"→ ~${(f['expense_cost'] or 0):,.2f}/yr"
                )

        if p["goals"]:
            click.echo("\n  Goals:")
            for g in p["goals"]:
                dot = {"green": "OK ", "yellow": "WATCH", "red": "BEHIND", "info": "   "}[g["status"]]
                if g["target_amount"]:
                    click.echo(
                        f"    [{dot}] {g['name']:<25} "
                        f"${g['current']:,.2f} / ${g['target_amount']:,.2f}"
                    )
                else:
                    click.echo(f"    [{dot}] {g['name']:<25} ${g['current']:,.2f}")

        if p["suggested_actions"]:
            click.echo("\n  Suggested actions:")
            for i, a in enumerate(p["suggested_actions"], 1):
                click.echo(f"    {i}. {a}")
        if p.get("written_to"):
            click.echo(f"\nWritten to: {p['written_to']}")

    emit(ctx, payload, _render)


def _suggest_quarterly_actions(
    rate: dict,
    goals: list[dict],
    drift_rows: list[dict],
    fees_result: dict,
) -> list[str]:
    """Heuristic defaults — the AI rewrites with voice. Priority:
      1. Breach-level allocation drift
      2. Red-status goal
      3. Expense-ratio flag
      4. Low savings rate
    """
    out: list[str] = []
    breaches = [d for d in drift_rows
                if d["drift_pp"] is not None and abs(d["drift_pp"]) > 5.0]
    breaches.sort(key=lambda d: -abs(d["drift_pp"]))
    if breaches:
        d = breaches[0]
        direction = "reduce" if d["drift_pp"] > 0 else "add to"
        out.append(
            f"Rebalance: {direction} {d['asset_class']} by "
            f"{abs(d['drift_pp']):.1f}pp (drift breach)."
        )
    red_goal = next((g for g in goals if g["status"] == "red"), None)
    if red_goal and len(out) < 3:
        out.append(f"Revisit goal '{red_goal['name']}' — behind pace or past target.")
    if fees_result["flagged"] and len(out) < 3:
        worst = fees_result["flagged"][0]
        out.append(
            f"Fee review: {worst['account']} expense ratio is "
            f"{worst['expense_ratio_pct']:.3f}% "
            f"(~${(worst['expense_cost'] or 0):,.2f}/yr) — consider swapping "
            f"to a lower-cost index fund of the same asset class."
        )
    if rate["rate"] is not None and rate["rate"] < 0.10 and len(out) < 3:
        out.append(
            f"Savings rate is {rate['rate']*100:.1f}% this quarter — aim for 10%+."
        )
    return out


def _render_quarterly_markdown(p: dict) -> str:
    t = p["totals"]
    r = p["savings_rate"]
    nw = p["net_worth"]
    qoq = p["quarter_over_quarter"]

    lines = [
        "---",
        f"quarter: {p['quarter']}",
        f"start: {p['start']}",
        f"end: {p['end']}",
        "type: quarterly-review",
        f"generated_at: {datetime.now().isoformat(timespec='seconds')}",
        "---",
        "",
        f"# Quarterly review — {p['quarter']}",
        "",
        "## Quarter in review",
        "",
        f"Net worth moved from **${nw['beginning']:,.2f}** to "
        f"**${nw['ending']:,.2f}** "
        f"({'+' if nw['delta']>=0 else ''}${nw['delta']:,.2f}"
        + (f", {nw['delta_pct']:+.2f}%" if nw['delta_pct'] is not None else "")
        + ").",
        "",
        "## Cash flow",
        "",
        f"- Inflow: **${t['inflow']:,.2f}**",
        f"- Outflow: **${t['outflow']:,.2f}**",
        f"- Net: **${t['net']:+,.2f}**",
    ]
    if r["rate"] is not None:
        lines.append(
            f"- Savings rate: **{r['rate']*100:.1f}%** "
            f"(${r['saved']:,.2f} of ${r['income']:,.2f})"
        )
    if qoq["outflow_delta_pct"] is not None:
        sign = "+" if qoq["outflow_delta"] >= 0 else ""
        lines.append(
            f"- vs {qoq['prior_quarter']}: outflow {sign}${qoq['outflow_delta']:,.2f} "
            f"({sign}{qoq['outflow_delta_pct']:.1f}%)"
        )
    lines.append("")

    lines.append("## Rebalance check")
    lines.append("")
    if p["allocation"]["targets_set"]:
        for row in p["allocation"]["drift"]:
            tgt = (
                f"{row['target_pct']:.1f}%" if row["target_pct"] is not None else "—"
            )
            drift = (
                f"{row['drift_pp']:+.1f}pp" if row["drift_pp"] is not None else "—"
            )
            lines.append(
                f"- **{row['asset_class']}** — current {row['current_pct']:.1f}%, "
                f"target {tgt}, drift {drift}"
            )
    else:
        lines.append("_No allocation targets set. Populate `allocation_targets` "
                     "to enable drift-based rebalancing._")
    lines.append("")

    lines.append("## Fee audit")
    lines.append("")
    f = p["fees"]
    lines.append(
        f"Estimated total annual cost: **${f['total_annual_cost']:,.2f}** "
        f"(threshold {f['threshold_pct']:.2f}%)."
    )
    lines.append("")
    if f["flagged"]:
        lines.append("Flagged accounts (expense ratio above threshold):")
        lines.append("")
        for row in f["flagged"]:
            lines.append(
                f"- **{row['account']}** — expense ratio "
                f"{row['expense_ratio_pct']:.3f}%, "
                f"~${(row['expense_cost'] or 0):,.2f}/yr on "
                f"${(row['balance'] or 0):,.0f}"
            )
        lines.append("")
    if f["missing_fee_info"]:
        lines.append(
            "Accounts with no recorded fee info: "
            + ", ".join(f["missing_fee_info"])
        )
        lines.append("")

    lines.append("## Goals")
    lines.append("")
    dot = {"green": "🟢", "yellow": "🟡", "red": "🔴", "info": "⚪"}
    if p["goals"]:
        for g in p["goals"]:
            if g["target_amount"]:
                lines.append(
                    f"- {dot[g['status']]} **{g['name']}** — "
                    f"${g['current']:,.2f} / ${g['target_amount']:,.2f}"
                    + (f" (target: {g['target_date']})" if g["target_date"] else "")
                )
            else:
                lines.append(f"- {dot[g['status']]} **{g['name']}** — ${g['current']:,.2f}")
    else:
        lines.append("_No active goals._")
    lines.append("")

    if p["by_category"]:
        lines.append("## Spending by category")
        lines.append("")
        for b in p["by_category"][:8]:
            if b["outflow"] > 0:
                lines.append(
                    f"- **{b['key']}** — ${b['outflow']:,.2f} ({b['count']} txns)"
                )
        lines.append("")

    if p["suggested_actions"]:
        lines.append("## Suggested actions")
        lines.append("")
        for i, a in enumerate(p["suggested_actions"], 1):
            lines.append(f"{i}. {a}")
        lines.append("")

    return "\n".join(lines)


@report.command("annual")
@click.option("--year", default=None, type=int, help="Year: YYYY. Default: last complete year.")
@click.option("--write/--no-write", default=False, show_default=True,
              help="Write the review to reports/YYYY-annual.md")
@click.pass_context
def annual(ctx: click.Context, year: int | None, write: bool) -> None:
    """Annual review payload.

    Full-year aggregates plus tax-pack numbers, allocation, fees, goals,
    and year-over-year comparison. The AI composes the prose; --write
    persists a default markdown review to `reports/YYYY-annual.md`.
    """
    config = resolve_config(ctx.obj.get("db_override"))
    ensure_data_dirs(config)

    if year is None:
        year = date.today().year - 1

    try:
        start, end = parse_year(str(year))
    except ValueError as e:
        emit_error(ctx, str(e), code="bad_year")
        return

    prior_start, prior_end = parse_year(str(year - 1))

    conn = connect(config.db_path)
    try:
        totals = cashflow_totals(conn, start, end)
        prior_totals = cashflow_totals(conn, prior_start, prior_end)
        rate = savings_rate(conn, start, end)
        by_cat = cashflow_by(conn, start, end, by="category")
        by_merchant = cashflow_by(conn, start, end, by="merchant")
        goals = goal_progress(conn, end)
        anoms = all_anomalies(conn, start, end)
        nw_start = networth_at(conn, start - timedelta(days=1))
        nw_end = networth_at(conn, end)
        pack = tax_pack(conn, year)
        alloc = current_allocation(conn, end)
        targets_obj = allocation_targets(conn, end)
        fees_result = fee_audit(conn, end, threshold_pct=0.25)
    finally:
        conn.close()

    nw_delta = nw_end["net_worth"] - nw_start["net_worth"]
    nw_delta_pct = (
        (nw_delta / nw_start["net_worth"] * 100) if nw_start["net_worth"] else None
    )
    outflow_delta = totals["outflow"] - prior_totals["outflow"]
    outflow_delta_pct = (
        (outflow_delta / prior_totals["outflow"] * 100)
        if prior_totals["outflow"] > 0 else None
    )

    targets_map = targets_obj["targets"]
    current_map = {c["asset_class"]: c for c in alloc["by_class"]}
    drift_rows: list[dict] = []
    for ac in sorted(set(current_map.keys()) | set(targets_map.keys())):
        cur_pct = current_map[ac]["pct"] if ac in current_map else 0.0
        tgt_pct = targets_map.get(ac)
        drift_rows.append({
            "asset_class": ac,
            "current_pct": cur_pct,
            "target_pct": tgt_pct,
            "drift_pp": (round(cur_pct - tgt_pct, 2) if tgt_pct is not None else None),
        })

    payload = {
        "ok": True,
        "year": int(year),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "totals": totals,
        "savings_rate": rate,
        "net_worth": {
            "beginning": nw_start["net_worth"],
            "beginning_as_of": nw_start["oldest_balance_as_of"],
            "ending": nw_end["net_worth"],
            "ending_as_of": nw_end["oldest_balance_as_of"],
            "delta": nw_delta,
            "delta_pct": nw_delta_pct,
        },
        "year_over_year": {
            "prior_year": int(year) - 1,
            "prior_outflow": prior_totals["outflow"],
            "outflow_delta": outflow_delta,
            "outflow_delta_pct": outflow_delta_pct,
        },
        "by_category": [bucket_to_dict(b) for b in by_cat[:15]],
        "by_merchant": [bucket_to_dict(b) for b in by_merchant[:10]],
        "goals": goals,
        "tax_pack": pack,
        "allocation": {
            "assets_total": alloc["assets_total"],
            "by_class": alloc["by_class"],
            "targets": targets_map,
            "targets_set": bool(targets_map),
            "drift": drift_rows,
        },
        "fees": {
            "total_annual_cost": fees_result["total_annual_cost"],
            "threshold_pct": fees_result["threshold_pct"],
            "flagged": fees_result["flagged"],
            "missing_fee_info": fees_result["missing_fee_info"],
        },
        "anomalies": [anomaly_to_dict(a) for a in anoms[:15]],
    }

    if write:
        body = _render_annual_markdown(payload)
        written = _write_report(config.reports_dir, f"{year}-annual.md", body)
        payload["written_to"] = str(written)

    def _render(p: dict) -> None:
        click.echo(f"Annual review — {p['year']}  ({p['start']} → {p['end']})")
        t = p["totals"]
        click.echo(
            f"  Cashflow:  in ${t['inflow']:>12,.2f}  out ${t['outflow']:>12,.2f}  "
            f"net ${t['net']:>+12,.2f}"
        )
        r = p["savings_rate"]
        if r["rate"] is not None:
            click.echo(
                f"  Savings:   ${r['saved']:,.2f} of ${r['income']:,.2f} "
                f"({r['rate']*100:+.1f}%)"
            )
        nw = p["net_worth"]
        sign = "+" if nw["delta"] >= 0 else ""
        click.echo(
            f"  Net worth: ${nw['beginning']:,.2f} → ${nw['ending']:,.2f}  "
            f"({sign}${nw['delta']:,.2f})"
        )
        yoy = p["year_over_year"]
        click.echo(
            f"  vs {yoy['prior_year']}: outflow "
            f"{'+$' if yoy['outflow_delta']>=0 else '-$'}{abs(yoy['outflow_delta']):,.2f}"
        )

        pack = p["tax_pack"]
        click.echo(f"\n  Tax pack — income ${pack['income']['total']:,.2f}")
        if pack["notable"]:
            for label, rows in pack["notable"].items():
                total = sum(r["total"] for r in rows)
                click.echo(
                    f"    {label}: ${total:,.2f} across {len(rows)} cat(s)"
                )
        click.echo(f"    ({pack['disclaimer']})")

        if p["goals"]:
            click.echo("\n  Goals:")
            for g in p["goals"]:
                dot = {"green": "OK ", "yellow": "WATCH", "red": "BEHIND", "info": "   "}[g["status"]]
                if g["target_amount"]:
                    click.echo(
                        f"    [{dot}] {g['name']:<25} "
                        f"${g['current']:,.2f} / ${g['target_amount']:,.2f}"
                    )
                else:
                    click.echo(f"    [{dot}] {g['name']:<25} ${g['current']:,.2f}")

        if p.get("written_to"):
            click.echo(f"\nWritten to: {p['written_to']}")

    emit(ctx, payload, _render)


def _render_annual_markdown(p: dict) -> str:
    t = p["totals"]
    r = p["savings_rate"]
    nw = p["net_worth"]
    yoy = p["year_over_year"]
    pack = p["tax_pack"]

    lines = [
        "---",
        f"year: {p['year']}",
        f"start: {p['start']}",
        f"end: {p['end']}",
        "type: annual-review",
        f"generated_at: {datetime.now().isoformat(timespec='seconds')}",
        "---",
        "",
        f"# Annual review — {p['year']}",
        "",
        "## The year in review",
        "",
        f"Net worth moved from **${nw['beginning']:,.2f}** to "
        f"**${nw['ending']:,.2f}** "
        f"({'+' if nw['delta']>=0 else ''}${nw['delta']:,.2f}"
        + (f", {nw['delta_pct']:+.2f}%" if nw['delta_pct'] is not None else "")
        + ").",
        "",
        "## Cash flow totals",
        "",
        f"- Inflow: **${t['inflow']:,.2f}**",
        f"- Outflow: **${t['outflow']:,.2f}**",
        f"- Net: **${t['net']:+,.2f}**",
    ]
    if r["rate"] is not None:
        lines.append(
            f"- Savings rate: **{r['rate']*100:.1f}%** "
            f"(${r['saved']:,.2f} of ${r['income']:,.2f})"
        )
    if yoy["outflow_delta_pct"] is not None:
        sign = "+" if yoy["outflow_delta"] >= 0 else ""
        lines.append(
            f"- vs {yoy['prior_year']}: outflow {sign}${yoy['outflow_delta']:,.2f} "
            f"({sign}{yoy['outflow_delta_pct']:.1f}%)"
        )
    lines.append("")

    lines.append("## Goal progress")
    lines.append("")
    dot = {"green": "🟢", "yellow": "🟡", "red": "🔴", "info": "⚪"}
    if p["goals"]:
        for g in p["goals"]:
            if g["target_amount"]:
                lines.append(
                    f"- {dot[g['status']]} **{g['name']}** — "
                    f"${g['current']:,.2f} / ${g['target_amount']:,.2f}"
                    + (f" (target: {g['target_date']})" if g['target_date'] else "")
                )
            else:
                lines.append(f"- {dot[g['status']]} **{g['name']}** — ${g['current']:,.2f}")
    else:
        lines.append("_No active goals._")
    lines.append("")

    lines.append("## Tax prep handoff")
    lines.append("")
    lines.append(f"- **Gross income (tagged):** ${pack['income']['total']:,.2f}")
    if pack["income"]["by_source"]:
        for row in pack["income"]["by_source"]:
            lines.append(
                f"  - {row['category']}: ${row['total']:,.2f} ({row['count']} txns)"
            )
    if pack["notable"]:
        lines.append("")
        lines.append("Potentially tax-relevant category matches:")
        lines.append("")
        for label, rows in pack["notable"].items():
            total = sum(r["total"] for r in rows)
            cats = ", ".join(f"{r['category']} (${r['total']:,.2f})" for r in rows)
            lines.append(f"- **{label}** — ${total:,.2f} total. Categories: {cats}")
    lines.append("")
    lines.append(f"_{pack['disclaimer']}_")
    lines.append("")

    lines.append("## Allocation")
    lines.append("")
    if p["allocation"]["targets_set"]:
        for row in p["allocation"]["drift"]:
            tgt = (
                f"{row['target_pct']:.1f}%" if row["target_pct"] is not None else "—"
            )
            drift = (
                f"{row['drift_pp']:+.1f}pp" if row["drift_pp"] is not None else "—"
            )
            lines.append(
                f"- **{row['asset_class']}** — current {row['current_pct']:.1f}%, "
                f"target {tgt}, drift {drift}"
            )
    else:
        lines.append("_No allocation targets set._")
    lines.append("")

    f = p["fees"]
    lines.append("## Fees")
    lines.append("")
    lines.append(
        f"Estimated total annual cost: **${f['total_annual_cost']:,.2f}**."
    )
    if f["flagged"]:
        lines.append("")
        lines.append("Flagged accounts:")
        for row in f["flagged"]:
            lines.append(
                f"- **{row['account']}** — expense ratio "
                f"{row['expense_ratio_pct']:.3f}%"
            )
    lines.append("")

    lines.append("## Insurance & estate")
    lines.append("")
    lines.append(
        "Review `state/insurance.md` and `state/estate.md` during the annual "
        "sit-down. The CLI does not check coverage adequacy or beneficiary "
        "accuracy — that's a human read-through."
    )
    lines.append("")

    lines.append("## Philosophy check")
    lines.append("")
    lines.append(
        "Re-read `principles.md` and `rules.md`. A year of data may warrant "
        "edits; this is the place to make them."
    )
    lines.append("")

    if p["by_category"]:
        lines.append("## Top spending categories")
        lines.append("")
        for b in p["by_category"][:10]:
            if b["outflow"] > 0:
                lines.append(
                    f"- **{b['key']}** — ${b['outflow']:,.2f} ({b['count']} txns)"
                )
        lines.append("")

    return "\n".join(lines)
