"""Museum originals: alt-review provenance and non-fabrication guard."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audit_museum_alt_provenance import build_review

class MuseumSourceAltReviewTests(unittest.TestCase):
    def test_source_provenance_and_explicit_manual_review(self):
        rows,summary=build_review(ROOT)
        self.assertGreaterEqual(summary["total_html_pages"],900)
        self.assertEqual(summary["total_audit_occurrences"],0)
        # No automatic ALT_POLICY issues in local HTML does not prove human screen-reader acceptance.
        self.assertEqual(sum(r["render_occurrences"] for r in rows),summary["total_audit_occurrences"])
        self.assertEqual(len(rows),summary["unique_image_and_alt_pairs"])
        self.assertEqual(summary["unlinked_source_pairs"],0)
        for row in rows:
            self.assertTrue(row["original_museum_source_url"].startswith("https://muzei-xleb.ru/"))
            self.assertTrue(row["manual_review_reason"].endswith("REVIEW_REQUIRED"))
            self.assertGreater(row["page_count"],0)
            self.assertFalse(row["manual_review_reason"].startswith("AUTO_CAPTION"))
    def test_review_deterministic(self):
        first,stats=build_review(ROOT)
        second,again=build_review(ROOT)
        self.assertEqual(first,second)
        self.assertEqual(stats,again)

if __name__=="__main__":
    unittest.main()
