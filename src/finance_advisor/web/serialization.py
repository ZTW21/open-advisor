"""Helpers to serialize analytics dataclasses to JSON-safe dicts."""

from __future__ import annotations

from finance_advisor.analytics import Anomaly, CashflowBucket, Debt


def anomaly_to_dict(a: Anomaly) -> dict:
    return {
        "kind": a.kind,
        "severity": a.severity,
        "subject": a.subject,
        "detail": a.detail,
        "amount": a.amount,
        "txn_id": a.txn_id,
        "date": a.date,
    }


def bucket_to_dict(b: CashflowBucket) -> dict:
    return {
        "key": b.key,
        "inflow": b.inflow,
        "outflow": b.outflow,
        "net": b.net,
        "count": b.count,
    }


def debt_to_dict(d: Debt) -> dict:
    return {
        "account_id": d.account_id,
        "name": d.name,
        "account_type": d.account_type,
        "balance": d.balance,
        "apr": d.apr,
        "min_payment": d.min_payment,
        "as_of_date": d.as_of_date,
    }
