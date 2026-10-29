import base64
import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.build_csp import make_csp


class CspTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)

    def test_hashes_each_inline_script_without_inline_js_escape_hatch(self):
        script = "window.__musbread = { ready: true };"
        (self.root / "index.html").write_text(
            "<html><script>" + script + "</script><script src='/a.js'></script></html>")
        policy = make_csp(self.root)
        sha = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        self.assertIn("'sha256-" + sha + "'", policy)
        self.assertIn("script-src-attr 'none'", policy)
        self.assertNotIn("script-src 'self' 'unsafe-inline'", policy)
        self.assertNotIn("'unsafe-eval'", policy)
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertIn("frame-src https://yandex.ru https://vk.com https://vkvideo.ru", policy)
        self.assertNotIn("script-src 'self' https://vk.com",policy)
        self.assertNotIn("connect-src 'self' https://vk.com",policy)
        self.assertNotIn("script-src 'self' https://yandex.ru", policy)
        self.assertNotIn("connect-src 'self' https://yandex.ru", policy)
        self.assertIn("object-src 'none'", policy)

    def test_request_ingress_is_allowlisted_only_explicitly(self):
        (self.root / "index.html").write_text("<script>app()</script>")
        self.assertIn("connect-src 'self';", make_csp(self.root))
        approved = make_csp(self.root, "https://requests.musbread.ru")
        self.assertIn("connect-src 'self' https://requests.musbread.ru;", approved)
        self.assertNotIn("script-src 'self' https://requests.musbread.ru", approved)
        for invalid in ("http://requests.musbread.ru", "https://localhost:8080",
                        "https://private.local", "https://127.0.0.1", "https://a.example.com/path",
                        "https://user:pass@requests.musbread.ru"):
            with self.assertRaises(ValueError):
                make_csp(self.root, invalid)

    def test_collects_all_pages_not_just_home(self):
        (self.root / "index.html").write_text("<script>one()</script>")
        (self.root / "news").mkdir()
        (self.root / "news/index.html").write_text("<script>two()</script>")
        policy = make_csp(self.root)
        for body in ("one()", "two()"):
            sha = base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
            self.assertIn("'sha256-" + sha + "'", policy)

    def test_missing_build_rejected(self):
        with self.assertRaisesRegex(ValueError, "built"):
            make_csp(self.root)

    def test_inline_script_with_html_character_references_hashed_raw(self):
        script = 'const value = "&amp;";'
        (self.root / "index.html").write_text("<script>" + script + "</script>")
        policy = make_csp(self.root)
        sha = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        self.assertIn("'sha256-" + sha + "'", policy)


if __name__ == "__main__":
    unittest.main()
