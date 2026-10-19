"""Source-first SEO: do not silently shorten authoritative museum H1 titles.

These are WARNINGS not errors; history/news aliases must share a canonical
URL. Preview robots MUST remain noindex even when titles are long.
"""
from __future__ import annotations
import unittest
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

from scripts.audit_accessibility_content import Page,scan_page

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/"apps/web/out"

class MuseumLongOriginalTitles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.long=[]
        for path in sorted(BUILD.rglob("*.html")):
            rel=path.relative_to(BUILD).as_posix()
            _,warn,dom=scan_page(path,rel)
            for issue in warn:
                if issue["code"]=="LONG_TITLE":
                    cls.long.append((rel,dom))
    def test_all_long_titles_preserve_original_visible_heading(self):
        self.assertEqual(len(self.long),10)
        for rel,dom in self.long:
            with self.subTest(rel=rel):
                self.assertEqual(dom.title,dom.h1_texts[0]+" | Музей Хлеба")
                self.assertGreater(len(dom.title),125)
                self.assertTrue(dom.h1_texts[0])
                robots=[m.get("content","") for m in dom.elements("meta")
                        if m.get("name")=="robots"]
                self.assertTrue(any("noindex" in r for r in robots))
    def test_source_canonicals_and_historical_news_aliases(self):
        self.assertEqual(len({d.title for _,d in self.long}),8)
        mapped={}
        for rel,dom in self.long:
            link=[x["href"] for x in dom.elements("link") if "canonical" in x.get("rel","").split()]
            self.assertEqual(len(link),1,rel)
            u=urlsplit(link[0])
            self.assertEqual(u.netloc,"muzei-xleb.ru")
            self.assertEqual(u.scheme,"https")
            self.assertFalse(u.query or u.fragment)
            mapped.setdefault(dom.title,set()).add(link[0])
        # Two original news headlines have both /news/ and Drupal /novosty/
        # addresses; their canonical URL is the same genuine museum address.
        self.assertEqual(Counter(map(len,mapped.values())),Counter({1:8}))
    def test_no_preview_indexation(self):
        for rel,dom in self.long:
            meta=[m for m in dom.elements("meta") if m.get("name")=="robots"]
            self.assertTrue(meta and "nofollow" in meta[0].get("content",""),rel)

if __name__=="__main__": unittest.main()
