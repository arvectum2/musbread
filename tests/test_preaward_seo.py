import tempfile
import unittest
from pathlib import Path
from scripts.check_preaward_seo import check

class PreawardSeoTests(unittest.TestCase):
    def test_fails_when_search_indexing_is_turned_on(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "robots.txt").write_text("User-Agent: *\nAllow: /\n")
            (out / "sitemap.xml").write_text("<urlset></urlset>")
            (out / "index.html").write_text('<meta name="robots" content="index,follow">')
            with self.assertRaises(AssertionError):
                check(out)

if __name__ == "__main__":
    unittest.main()
