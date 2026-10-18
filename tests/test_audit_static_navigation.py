import tempfile
import unittest
from pathlib import Path

from scripts.audit_static_navigation import audit_links


class StaticNavigationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.site = Path(self.folder.name)
        (self.site / "index.html").write_text(
            '<h1 id="top">Home</h1><a tabindex="0" href="/news/">News</a><a tabindex="0" href="/#top">Top</a>')
        (self.site / "news").mkdir()
        (self.site / "news/index.html").write_text(
            '<h1 id="news">News</h1><a tabindex="0" href="../#top">Home</a>')

    def test_valid_internal_pages_and_anchors(self):
        self.assertEqual(audit_links(self.site), {"pages": 2, "verified_internal_links": 3})

    def test_missing_page_is_detected(self):
        (self.site / "index.html").write_text('<a tabindex="0" href="/absent/">Missing</a>')
        with self.assertRaisesRegex(ValueError, "missing static page"):
            audit_links(self.site)

    def test_broken_anchor_is_detected(self):
        (self.site / "index.html").write_text('<a tabindex="0" href="/news/#gone">Missing anchor</a>')
        with self.assertRaisesRegex(ValueError, "missing anchor"):
            audit_links(self.site)

    def test_external_links_without_native_webkit_tab_order_are_rejected(self):
        (self.site / "index.html").write_text(
            '<a href="https://muzei-xleb.ru/sites/default/files/page/file.pdf">Museum PDF</a>')
        with self.assertRaisesRegex(ValueError, "tabindex=0"):
            audit_links(self.site)

    def test_negative_tabindex_on_internal_link_is_rejected(self):
        (self.site / "index.html").write_text(
            '<a tabindex="-1" href="/news/">Inaccessible news</a>')
        with self.assertRaisesRegex(ValueError, "tabindex=0"):
            audit_links(self.site)

    def test_no_javascript_pseudo_links(self):
        (self.site / "index.html").write_text('<a tabindex="0" href="javascript:alert(1)">Bad</a>')
        with self.assertRaisesRegex(ValueError, "JavaScript URL"):
            audit_links(self.site)


if __name__ == "__main__":
    unittest.main()
