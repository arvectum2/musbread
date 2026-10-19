"""Fail the pre-award offline build on any new broken internal museum URL."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_museum_static_internal_links import audit

ROOT = Path(__file__).resolve().parents[1]


class StaticMuseumLinkIntegrityTests(unittest.TestCase):
    def test_valid_internal_href_and_img(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "news").mkdir()
            (root / "news/index.html").write_text('<a href="/">Home</a><img src="/ok.png">')
            (root / "index.html").write_text("<h1>Original home</h1>")
            (root / "ok.png").write_bytes(b"pixels")
            checked = audit(root)
            self.assertEqual(checked["checked_local_references"], 2)
            self.assertEqual(checked["unexpected_broken_local_links"], 0)

    def test_unexpected_broken_local_url_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "index.html").write_text('<a href="/missing-article/">Lost</a>')
            with self.assertRaisesRegex(AssertionError, "missing-article"):
                audit(root)

    def test_explicit_upstream_403_404_remain_reported_not_green(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "index.html").write_text(
                '<a href="/node/462">Restricted original event</a>'
                '<a href="/obratnaya-svyaz">Restricted original form</a>')
            checked = audit(root)
            self.assertEqual(checked["known_upstream_breaks"], 2)
            self.assertEqual(checked["resolved_local_references"], 0)

    def test_npm_release_alias_must_run_complete_guarded_builder(self):
        config = json.loads((ROOT / "apps/web/package.json").read_text())
        builder = "../../.venv/bin/python ../../scripts/build_complete_museum_static_release.py"
        self.assertEqual(config["scripts"]["build:museum-deploy"], builder + " --build")
        self.assertEqual(config["scripts"]["verify:museum-deploy"], builder + " --verify-only")


if __name__ == "__main__":
    unittest.main()
