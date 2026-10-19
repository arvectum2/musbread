"""TZ-193: visually reviewed original museum photos are source-linked and safe."""
from __future__ import annotations

import json
import re
import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audit_accessibility_content import Page, ALT_GENERIC

class ReviewedMuseumAltTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/"apps/web/src/data/official-museum-reviewed-alt.json").read_text(encoding="utf-8"))
        cls.alts=cls.data["photos"]
        cls.images_by_src=defaultdict(set)
        for file in (ROOT/"apps/web/out").rglob("*.html"):
            page=Page()
            page.feed(file.read_text(encoding="utf-8"))
            for img in page.elements("img"):
                cls.images_by_src[img.get("src","")].add(img.get("alt",""))

    def test_only_original_self_hosted_museum_images_and_accessible_text(self):
        self.assertEqual(self.data["editorial_status"],"DRAFT_FOR_MUSEUM_REVIEW")
        self.assertGreaterEqual(len(self.alts),100)
        source_paths=set()
        for name in ("official-museum-photo-assets.json","official-news-index-photo-assets.json",
                     "official-deep-news-image-assets.json","official-historical-exhibition-image-assets.json"):
            corpus=json.loads((ROOT/"apps/web/src/data"/name).read_text())
            source_paths.update(asset["path"] for asset in corpus["photos"].values())
        for path,caption in self.alts.items():
            with self.subTest(path=path):
                self.assertRegex(path,r"^/media/museum-source/[a-f0-9]{64}\.webp$")
                self.assertIn(path,source_paths)
                self.assertTrue((ROOT/"apps/web/out"/path.lstrip("/")).is_file())
                self.assertGreaterEqual(len(caption),15)
                self.assertLessEqual(len(caption),125)
                self.assertNotRegex(caption,r"<|>|\u0000")
                self.assertIsNone(ALT_GENERIC.search(caption))

    def test_real_generated_html_shows_reviewed_wording_where_source_alt_missing(self):
        applied=[]
        retained=[]
        for path,caption in self.alts.items():
            values=self.images_by_src.get(path,set())
            self.assertTrue(values, "Reviewed museum image absent in assembled HTML: "+path)
            if caption in values:
                applied.append(path)
            else:
                # Museums may provide a curator caption in their source HTML.
                self.assertTrue(all(" — фотография " not in alt for alt in values),
                                "Meaningless numbered placeholder survived despite visual review: "+path)
                retained.append(path)
        self.assertGreaterEqual(len(applied),90)
        self.assertEqual(len(applied)+len(retained),len(self.alts))

if __name__=="__main__":
    unittest.main()
