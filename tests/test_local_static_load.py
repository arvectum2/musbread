"""TZ-317 loopback load tester: deterministic smoke and safety bounds."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "qa_local_static_load.py"


class LocalLoadTest(unittest.TestCase):
    def test_local_static_export_report(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            for part in ["", "events", "guide/museum", "search"]:
                target = base / "out" / part / "index.html"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("<html><body>Mock approved test fixture</body></html>", encoding="utf-8")
            output = base / "outcome.json"
            report = base / "report.md"
            done = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(base / "out"),
                 "--requests-per-route", "3", "--workers", "2",
                 "--output", str(output), "--report", str(report)],
                capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["external_hosts_tested"], 0)
            self.assertEqual(sum(row["total"] for row in result["routes"]), 12)
            self.assertTrue(all(row["ok_200"] == 3 and row["errors"] == 0 for row in result["routes"]))
            self.assertIn("не нагрузочные испытания промышленного", report.read_text(encoding="utf-8"))

    def test_rejects_unbounded_requests_before_opening_server(self):
        with tempfile.TemporaryDirectory() as directory:
            done = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", directory,
                 "--requests-per-route", "10000"], capture_output=True, text=True, timeout=5,
            )
            self.assertNotEqual(done.returncode, 0)
            self.assertIn("Limits:", done.stderr)


if __name__ == "__main__":
    unittest.main()
