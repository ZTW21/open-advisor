"""Report generation endpoints — mirrors commands/report.py payloads."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

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
from finance_advisor.web.deps import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/daily")
def daily_report(
    date_spec: str | None = Query(None, alias="date", description="YYYY-MM-DD, default yesterday"),
    conn: sqlite3.Connection = Depends(get_db),
):
    target = date.fromisoformat(date_spec) if date_spec else date.today() - timedelta(days=1)
    start = end = target

    totals = cashflow_totals(conn, start, end)
    buckets = cashflow_by(conn, start, end, by="merchant")
    anoms = all_anomalies(conn, start, end)
    week_start = target - timedelta(days=6)
    week_totals = cashflow_totals(conn, week_start, target)

    return {
        "ok": True,
        "date": target.isoformat(),
        "totals": totals,
        "rolling_7d": {"start": week_start.isoformat(), "end": target.isoformat(), **week_totals},
        "top_merchants_today": [bucket_to_dict(b) for b in buckets[:3]],
        "anomalies": [anomaly_to_dict(a) for a in anoms],
    }


@router.get("/weekly")
def weekly_report(
    week: str | None = Query(None, description="YYYY-Www, default last complete week"),
    conn: sqlite3.Connection = Depends(get_db),
):
    if week:
        start, end = parse_iso_week(week)
    else:
        today = date.today()
        days_since_sunday = (today.weekday() + 1) % 7
        last_sunday = today - timedelta(days=days_since_sunday or 7)
        start = last_sunday - timedelta(days=6)
        end = last_sunday
    week_label = format_iso_week(start)

    totals = cashflow_totals(conn, start, end)
    by_cat = cashflow_by(conn, start, end, by="category")
    by_merchant = cashflow_by(conn, start, end, by="merchant")
    anoms = all_anomalies(conn, start, end)

    prior_totals = []
    for i in range(1, 5):
        p_end = start - timedelta(days=1 + 7 * (i - 1))
        p_start = p_end - timedelta(days=6)
        prior_totals.append(cashflow_totals(conn, p_start, p_end)["outflow"])
    prior_median = sorted(prior_totals)[len(prior_totals) // 2] if prior_totals else 0.0
    pace_delta = totals["outflow"] - prior_median
    pace_pct = (pace_delta / prior_median * 100) if prior_median else None

    return {
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


@router.get("/monthly")
def monthly_report(
    month: str | None = Query(None, description="YYYY-MM, default last complete month"),
    conn: sqlite3.Connection = Depends(get_db),
):
    if month:
        start, end = parse_month(month)
        month_label = month
    else:
        today = date.today()
        if today.month == 1:
            yr, mo = today.year - 1, 12
        else:
            yr, mo = today.year, today.month - 1
        month_label = f"{yr:04d}-{mo:02d}"
        start, end = parse_month(month_label)

    if start.month == 1:
        py, pm = start.year - 1, 12
    else:
        py, pm = start.year, start.month - 1
    prior_label = f"{py:04d}-{pm:02d}"
    prior_start, prior_end = parse_month(prior_label)

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

    nw_delta = nw_end["net_worth"] - nw_start["net_worth"]
    nw_delta_pct = (nw_delta / nw_start["net_worth"] * 100) if nw_start["net_worth"] else None
    outflow_delta = totals["outflow"] - prior_totals["outflow"]
    outflow_delta_pct = (outflow_delta / prior_totals["outflow"] * 100) if prior_totals["outflow"] > 0 else None

    return {
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
    }


@router.get("/quarterly")
def quarterly_report(
    quarter: str | None = Query(None, description="YYYY-Qn, default last complete quarter"),
    fee_threshold: float = Query(0.25),
    conn: sqlite3.Connection = Depends(get_db),
):
    if quarter:
        start, end = parse_quarter(quarter)
        label = f"{start.year:04d}-Q{(start.month - 1) // 3 + 1}"
    else:
        today = date.today()
        current_q = (today.month - 1) // 3 + 1
        from calendar import monthrange
        last_month_of_q = 3 * current_q
        last_day_of_q = monthrange(today.year, last_month_of_q)[1]
        end_of_current_q = date(today.year, last_month_of_q, last_day_of_q)
        if today <= end_of_current_q:
            if current_q == 1:
                label = f"{today.year - 1:04d}-Q4"
            else:
                label = f"{today.year:04d}-Q{current_q - 1}"
        else:
            label = f"{today.year:04d}-Q{current_q}"
        start, end = parse_quarter(label)

    prior_label = prior_quarter(label)
    prior_start, prior_end = parse_quarter(prior_label)

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

    nw_delta = nw_end["net_worth"] - nw_start["net_worth"]
    nw_delta_pct = (nw_delta / nw_start["net_worth"] * 100) if nw_start["net_worth"] else None
    outflow_delta = totals["outflow"] - prior_totals["outflow"]
    outflow_delta_pct = (outflow_delta / prior_totals["outflow"] * 100) if prior_totals["outflow"] > 0 else None

    targets_map = targets_obj["targets"]
    current_map = {c["asset_class"]: c for c in alloc["by_class"]}
    drift_rows = []
    for ac in sorted(set(current_map.keys()) | set(targets_map.keys())):
        cur_pct = current_map[ac]["pct"] if ac in current_map else 0.0
        tgt_pct = targets_map.get(ac)
        drift_rows.append({
            "asset_class": ac,
            "current_pct": cur_pct,
            "target_pct": tgt_pct,
            "drift_pp": round(cur_pct - tgt_pct, 2) if tgt_pct is not None else None,
        })

    return {
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
    }


@router.get("/annual")
def annual_report(
    year: int | None = Query(None, description="YYYY, default last complete year"),
    conn: sqlite3.Connection = Depends(get_db),
):
    if year is None:
        year = date.today().year - 1

    start, end = parse_year(str(year))
    prior_start, prior_end = parse_year(str(year - 1))

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

    nw_delta = nw_end["net_worth"] - nw_start["net_worth"]
    nw_delta_pct = (nw_delta / nw_start["net_worth"] * 100) if nw_start["net_worth"] else None
    outflow_delta = totals["outflow"] - prior_totals["outflow"]
    outflow_delta_pct = (outflow_delta / prior_totals["outflow"] * 100) if prior_totals["outflow"] > 0 else None

    targets_map = targets_obj["targets"]
    current_map = {c["asset_class"]: c for c in alloc["by_class"]}
    drift_rows = []
    for ac in sorted(set(current_map.keys()) | set(targets_map.keys())):
        cur_pct = current_map[ac]["pct"] if ac in current_map else 0.0
        tgt_pct = targets_map.get(ac)
        drift_rows.append({
            "asset_class": ac,
            "current_pct": cur_pct,
            "target_pct": tgt_pct,
            "drift_pp": round(cur_pct - tgt_pct, 2) if tgt_pct is not None else None,
        })

    return {
        "ok": True,
        "year": year,
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
            "prior_year": year - 1,
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
