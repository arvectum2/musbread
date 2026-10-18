"""Real image inventory across eleven halls and historical building, no substitutes."""
from __future__ import annotations

import csv
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT/'docs/source-migration/EXPOSITION_GALLERY_COVERAGE_20261018.csv'


class RoomPhotoCoverageTests(unittest.TestCase):
    def test_source_coverage_is_truthful_and_exact(self):
        with CSV.open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f,delimiter=';'))
        self.assertEqual(len(rows),12)
        self.assertEqual(len({row['cms_slug'] for row in rows}),12)
        self.assertEqual(sum(int(row['total_real_original_images']) for row in rows),100)
        self.assertEqual(sum(int(row['archived_original_images']) for row in rows),48)
        self.assertEqual(sum(int(row['still_to_copy']) for row in rows),52)
        rooms=[r for r in rows if r['cms_slug'].startswith('zal-')]
        self.assertEqual(len(rooms),11)
        for row in rooms:
            self.assertEqual(int(row['archived_original_images']),3)
            self.assertEqual(int(row['still_to_copy']),
                             int(row['total_real_original_images'])-3)
            self.assertTrue(row['original_page_url'].startswith('https://muzei-xleb.ru/'))
            self.assertEqual(row['rights_status'],'private-not-verified')
        history=next(x for x in rows if x['cms_slug']=='building-history')
        self.assertEqual((int(history['archived_original_images']),
                          int(history['total_real_original_images'])),(15,15))
        self.assertEqual(history['next_original_image_index'],'')


if __name__=='__main__':
    unittest.main()
