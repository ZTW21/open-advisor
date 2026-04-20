"""SimpleFIN Bridge HTTP client — pure functions, stdlib only.

SimpleFIN API summary:
  - Setup token is a base64-encoded claim URL.
  - POST to the claim URL (once) returns an access URL with embedded
    HTTP Basic Auth credentials.
  - GET {access_url}/accounts returns accounts + transactions.
  - Dates are Unix epoch seconds. Amounts are numeric strings.
  - Sign convention matches ours: positive = inflow, negative = outflow.
  - Rate limit: ~24 requests/day, 90-day max window.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from finance_advisor.sync.base import SyncError


def _parse_access_url(access_url: str) -> tuple[str, str, str]:
    """Split an access URL into (base_url, username, password).

    Access URLs look like: https://user:pass@host/simplefin
    """
    parsed = urlparse(access_url)
    if not parsed.username or not parsed.password:
        raise SyncError(
            "bad_token",
            "Access URL does not contain credentials. "
            "Re-run setup with a fresh setup token from SimpleFIN Bridge.",
        )
    base = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        base += f":{parsed.port}"
    base += parsed.path
    return base, parsed.username, parsed.password


def claim_token(setup_token: str) -> str:
    """Exchange a one-time setup token for a permanent access URL.

    The setup token is base64-encoded. Decoding gives a claim URL.
    POSTing to the claim URL returns the access URL as plain text.

    Raises SyncError on failure (token already claimed, network error, etc.).
    """
    try:
        claim_url = base64.b64decode(setup_token.strip()).decode("utf-8")
    except Exception as exc:
        raise SyncError(
            "bad_token",
            f"Could not decode setup token (expected base64): {exc}",
        ) from exc

    if not claim_url.startswith("http"):
        raise SyncError(
            "bad_token",
            f"Decoded token does not look like a URL: {claim_url[:60]}...",
        )

    req = urllib.request.Request(claim_url, method="POST", data=b"")
    req.add_header("User-Agent", "open-advisor/1.0")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            access_url = resp.read().decode("utf-8").strip()
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise SyncError(
                "token_claimed",
                "This setup token has already been claimed. "
                "Generate a new one at https://bridge.simplefin.org/simplefin/create",
            ) from exc
        raise SyncError(
            "claim_failed",
            f"SimpleFIN returned HTTP {exc.code} during token claim.",
        ) from exc
    except urllib.error.URLError as exc:
        raise SyncError(
            "network_error",
            f"Could not reach SimpleFIN Bridge: {exc.reason}",
        ) from exc

    # Validate the access URL has credentials
    _parse_access_url(access_url)
    return access_url


def _date_to_epoch(d: date) -> int:
    """Convert a date to Unix epoch seconds (midnight UTC)."""
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())


def fetch_accounts(
    access_url: str,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    account_ids: Optional[list[str]] = None,
    pending: bool = True,
    balances_only: bool = False,
) -> dict:
    """Fetch accounts (and optionally transactions) from SimpleFIN.

    Returns the parsed JSON response with keys: accounts, connections, errlist.
    Raises SyncError on auth/network failures.
    """
    base_url, username, password = _parse_access_url(access_url)

    params: list[str] = ["version=2"]
    if start_date:
        params.append(f"start-date={_date_to_epoch(start_date)}")
    if end_date:
        params.append(f"end-date={_date_to_epoch(end_date)}")
    if pending:
        params.append("pending=1")
    if balances_only:
        params.append("balances-only=1")
    if account_ids:
        for aid in account_ids:
            params.append(f"account={aid}")

    url = f"{base_url}/accounts?{'&'.join(params)}"

    # Send Basic Auth preemptively (SimpleFIN doesn't issue 401 challenges;
    # it returns 403 directly if credentials are missing).
    import base64 as _b64
    credentials = _b64.b64encode(f"{username}:{password}".encode()).decode()
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {credentials}")
    req.add_header("User-Agent", "open-advisor/1.0")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 402:
            raise SyncError(
                "payment_required",
                "SimpleFIN Bridge requires payment. Check your subscription at "
                "https://bridge.simplefin.org",
            ) from exc
        if exc.code == 403:
            raise SyncError(
                "auth_failed",
                "SimpleFIN rejected the access credentials. The token may have "
                "been revoked. Re-run setup with a fresh token.",
            ) from exc
        raise SyncError(
            "api_error",
            f"SimpleFIN returned HTTP {exc.code}.",
        ) from exc
    except urllib.error.URLError as exc:
        raise SyncError(
            "network_error",
            f"Could not reach SimpleFIN: {exc.reason}",
        ) from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SyncError(
            "bad_response",
            f"SimpleFIN returned invalid JSON: {exc}",
        ) from exc

    return data


def parse_transaction_date(epoch: int) -> str:
    """Convert a Unix epoch (seconds) to YYYY-MM-DD. Returns empty string for 0 (pending)."""
    if epoch == 0:
        return ""
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d")
