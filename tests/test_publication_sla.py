import hashlib
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import tempfile
import threading
import unittest

from scripts.publication_sla import (
    SCOPE, BUDGET_SECONDS, maximum_hourly_lag, measure, parse_utc,
    probe_local_http, write_private_result,
)

UTC = timezone.utc
NOW = datetime(2026, 10, 17, 16, 0, tzinfo=UTC)
PAGE = b'<!doctype html><html><body>QA approved v1</body></html>'
SHA = hashlib.sha256(PAGE).hexdigest()


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/redirect/":
            self.send_response(302)
            self.send_header("Location", "https://example.org/")
            self.end_headers()
            return
        if self.path != "/approved/" or self.server.missing:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(self.server.page_bytes)

    def log_message(self, *_args):
        pass


class PublicationSLATest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        cls.server.page_bytes = PAGE
        cls.server.missing = False
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        self.server.page_bytes = PAGE
        self.server.missing = False

    def audit(self, approved, observed, url="/approved/"):
        return measure(
            approval_id="QA-approved-1", approved_at=approved.isoformat(),
            page_url=self.base + url, expected_html_sha256=SHA, observed_at=observed,
        )

    def test_exact_content_observed_by_http_within_deadline(self):
        for seconds in (1, 3599, 3600):
            with self.subTest(seconds=seconds):
                row = self.audit(NOW, NOW + timedelta(seconds=seconds))
                self.assertEqual(row["status"], "verified_within_60m")
                self.assertEqual(row["scope"], SCOPE)
                self.assertEqual(row["http_status"], 200)
                self.assertEqual(row["observed_html_sha256"], SHA)
                self.assertEqual(row["seconds_since_approval"], seconds)

    def test_first_successful_probe_after_deadline_is_inconclusive(self):
        row = self.audit(NOW, NOW + timedelta(seconds=3601))
        self.assertEqual(row["status"], "late_first_observation_inconclusive")
        self.assertNotEqual(row["status"], "not_visible_after_deadline")

    def test_missing_or_wrong_page_changes_pending_to_overdue(self):
        self.server.page_bytes = PAGE + b"changed"
        early = self.audit(NOW, NOW + timedelta(seconds=3599))
        late = self.audit(NOW, NOW + timedelta(seconds=3601))
        self.assertEqual(early["status"], "pending_verification")
        self.assertEqual(late["status"], "not_visible_after_deadline")
        self.assertEqual(late["probe_error"], "content_hash_mismatch")
        exact_deadline = self.audit(NOW, NOW + timedelta(seconds=3600))
        self.assertEqual(exact_deadline["status"], "not_visible_after_deadline")
        self.server.missing = True
        failed = self.audit(NOW, NOW + timedelta(seconds=3660))
        self.assertEqual((failed["http_status"], failed["status"]), (404, "not_visible_after_deadline"))

    def test_redirect_is_never_followed(self):
        code, sha, error = probe_local_http(self.base + "/redirect/")
        self.assertEqual(code, 302)
        self.assertIsNone(sha)
        self.assertEqual(error, "http_status")

    def test_not_effective_until_explicit_approval(self):
        row = self.audit(NOW, NOW - timedelta(seconds=1))
        self.assertEqual(row["status"], "approval_not_yet_effective")
        self.assertIsNone(row["http_status"])

    def test_no_external_network_or_ambiguous_approval(self):
        for url in (
            "https://muzei-xleb.ru/", "http://example.org:80/approved/",
            "http://user:secret@127.0.0.1:1000/", "http://127.0.0.1/",
            "http://127.0.0.1:80/path#fragment",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    probe_local_http(url)
        with self.assertRaisesRegex(ValueError, "timezone"):
            parse_utc("2026-10-17T16:00:00")
        self.assertEqual(parse_utc("2026-10-17T19:00:00+03:00"), NOW)
        with self.assertRaisesRegex(ValueError, "approval reference"):
            measure(approval_id="../../private", approved_at=NOW.isoformat(),
                    page_url=self.base+"/approved/", expected_html_sha256=SHA, observed_at=NOW)
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            measure(approval_id="QA", approved_at=NOW.isoformat(),
                    page_url=self.base+"/approved/", expected_html_sha256="no", observed_at=NOW)

    def test_hourly_schedule_plus_positive_downstream_cannot_guarantee_60m(self):
        report = maximum_hourly_lag(remaining_build_transfer_seconds=120)
        self.assertEqual(report["worst_case_seconds"], 3720)
        self.assertFalse(report["within_60m_guarantee_possible"])
        self.assertTrue(maximum_hourly_lag(remaining_build_transfer_seconds=125,
                                          period_seconds=300)["within_60m_guarantee_possible"])
        with self.assertRaises(ValueError):
            maximum_hourly_lag(remaining_build_transfer_seconds=-1)

    def test_private_evidence_permissions_no_overwrite_or_public_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = self.audit(NOW, NOW + timedelta(minutes=12))
            path = root / "private" / "run.json"
            write_private_result(path, row)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text())["status"], "verified_within_60m")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                write_private_result(path, row)
            with self.assertRaisesRegex(ValueError, "public"):
                write_private_result(root/"out"/"sla.json", row)
            link = root / "private" / "fake.json"
            link.symlink_to(path)
            with self.assertRaisesRegex(ValueError, "overwrite"):
                write_private_result(link, row)


if __name__ == "__main__":
    unittest.main()
