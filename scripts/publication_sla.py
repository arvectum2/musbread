#!/usr/bin/env python3
"""TZ-110: local read-after-release verifier and conservative 60-minute SLA audit.

A successful CMS export, transfer or symlink swap is NOT public visibility.
This tool verifies exact public HTML bytes over HTTP on a bound LOCAL loopback
server. Approval timestamps come from an explicit independent record, never
from published_at (that is a scheduled eligibility date, not editorial approval).
No customer network is contacted.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler, Request
from urllib.error import HTTPError, URLError

BUDGET_SECONDS = 3600
MAX_HTML_BYTES = 4 * 1024 * 1024
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SCOPE = "LOCAL_PREAWARD_NOT_MUSEUM_PRODUCTION"


def parse_utc(value: str) -> datetime:
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("An explicit timezone offset is required")
    return instant.astimezone(timezone.utc)


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe_local_http(url: str) -> tuple[int | None, str | None, str | None]:
    """Return (status, sha256, safe error code), never follow redirects."""
    parsed = urlsplit(url)
    if (parsed.scheme != "http" or parsed.hostname not in
            {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password
            or parsed.fragment or parsed.port is None):
        raise ValueError("Only explicitly port-bound loopback HTTP URLs are allowed")
    opener = build_opener(ProxyHandler({}), NoRedirects)
    try:
        with opener.open(Request(url, headers={"Cache-Control": "no-cache"}), timeout=5) as response:
            if response.status != 200:
                return response.status, None, "unexpected_status"
            raw = response.read(MAX_HTML_BYTES + 1)
            if len(raw) > MAX_HTML_BYTES:
                return 200, None, "html_too_large"
            if not raw.lstrip().lower().startswith((b"<!doctype html", b"<html")):
                return 200, None, "not_html"
            return 200, hashlib.sha256(raw).hexdigest(), None
    except HTTPError as exc:
        try:
            return exc.code, None, "http_status"
        finally:
            exc.close()
    except (URLError, TimeoutError, OSError):
        return None, None, "network_error"


def measure(*, approval_id: str, approved_at: str, page_url: str,
            expected_html_sha256: str, observed_at: datetime | None = None) -> dict:
    """Never claim SLA for a late first successful observation."""
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}", approval_id):
        raise ValueError("Invalid approval reference (no personal data or paths)")
    if not SHA256.fullmatch(expected_html_sha256):
        raise ValueError("Invalid expected HTML SHA-256")
    approved = parse_utc(approved_at)
    checked = (observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if checked < approved:
        return {
            "scope": SCOPE, "approval_id": approval_id, "status": "approval_not_yet_effective",
            "approved_at_utc": approved.isoformat(), "observed_at_utc": checked.isoformat(),
            "deadline_utc": (approved + timedelta(seconds=BUDGET_SECONDS)).isoformat(),
            "seconds_since_approval": None, "expected_html_sha256": expected_html_sha256,
            "observed_html_sha256": None, "http_status": None, "probe_error": None,
        }
    http_status, observed_digest, error = probe_local_http(page_url)
    elapsed = round((checked - approved).total_seconds(), 3)
    verified = http_status == 200 and observed_digest == expected_html_sha256
    if verified:
        status = "verified_within_60m" if elapsed <= BUDGET_SECONDS else "late_first_observation_inconclusive"
    else:
        status = "not_visible_after_deadline" if elapsed >= BUDGET_SECONDS else "pending_verification"
        if http_status == 200 and observed_digest != expected_html_sha256:
            error = "content_hash_mismatch" if observed_digest else error
    return {
        "scope": SCOPE, "approval_id": approval_id, "status": status,
        "approved_at_utc": approved.isoformat(), "observed_at_utc": checked.isoformat(),
        "deadline_utc": (approved + timedelta(seconds=BUDGET_SECONDS)).isoformat(),
        "seconds_since_approval": elapsed, "expected_html_sha256": expected_html_sha256,
        "observed_html_sha256": observed_digest, "http_status": http_status,
        "probe_error": error,
    }


def maximum_hourly_lag(*, remaining_build_transfer_seconds: float, period_seconds: int = 3600) -> dict:
    """Analytic worst case: approval just AFTER one scheduled export."""
    if period_seconds <= 0 or remaining_build_transfer_seconds < 0:
        raise ValueError("Nonnegative measured pipeline duration and positive interval required")
    maximum = period_seconds + remaining_build_transfer_seconds
    return {
        "hourly_wait_upper_bound_seconds": period_seconds,
        "measured_downstream_seconds": remaining_build_transfer_seconds,
        "worst_case_seconds": maximum,
        "within_60m_guarantee_possible": maximum <= BUDGET_SECONDS,
        "recommendation": "Event-driven verified release or a shorter poll/dispatch interval is required"
        if maximum > BUDGET_SECONDS else "Prove actual end-to-end on the approved museum infrastructure",
    }


def write_private_result(path: Path, result: dict) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("Never overwrite an existing SLA evidence file")
    if any(part in {"out", "public", "releases"} for part in path.parts):
        raise ValueError("SLA evidence must be kept outside static/public directories")
    if path.parent.is_symlink():
        raise ValueError("Private evidence folder must not be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Exclusive create with strict permissions, no user details or server paths.
    fd = path.open("x", encoding="utf-8")
    try:
        import os
        os.fchmod(fd.fileno(), 0o600)
        json.dump(result, fd, indent=2, sort_keys=True)
        fd.write("\n")
        fd.flush()
        os.fsync(fd.fileno())
    finally:
        fd.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval-id", required=True)
    parser.add_argument("--approved-at", required=True, help="ISO 8601 with timezone; explicit actual approval")
    parser.add_argument("--url", required=True, help="HTTP loopback URL serving released HTML")
    parser.add_argument("--expected-sha256", required=True, help="Known release HTML SHA256")
    parser.add_argument("--output", required=True, type=Path, help="Private, new, non-public evidence JSON")
    args = parser.parse_args()
    result = measure(approval_id=args.approval_id, approved_at=args.approved_at,
                     page_url=args.url, expected_html_sha256=args.expected_sha256)
    write_private_result(args.output, result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
