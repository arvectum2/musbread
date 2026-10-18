"""Source-verified museum image metadata: no image generation or placeholder files."""
from __future__ import annotations
import csv,json,hashlib,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import cache_official_museum_photos as cache


class SourcePhotoInventoryTests(unittest.TestCase):
    def test_gallery_uses_only_literal_official_museum_urls(self):
        candidates=cache.queue()
        self.assertEqual(len(candidates),199)
        self.assertEqual(len({x['original_url'] for x in candidates}),len(candidates))
        self.assertTrue(all(x['original_url'].startswith('https://muzei-xleb.ru/sites/default/files/')
                            for x in candidates))
        self.assertTrue(all(x['source_page_url'].startswith('https://muzei-xleb.ru/')
                            for x in candidates))
        self.assertEqual(sum(x['source_image_index']==0 for x in candidates[:60]),27)
        self.assertEqual(len([x for x in candidates if x['cms_slug'].startswith('zal-')]),85)
        rooms=json.loads((ROOT/'apps/web/src/data/official-exposition-rooms.json').read_text())['rooms']
        for room in rooms:
            slug=room['slug']
            self.assertEqual({x['source_image_index'] for x in candidates if x['cms_slug']==slug},
                             set(range(len(room['image_sources']))))
        for index_slug in ('exhibitions-past','exhibitions-virtual'):
            self.assertEqual({x['source_image_index'] for x in candidates if x['cms_slug']==index_slug},set(range(12)))
        self.assertEqual({x['source_image_index'] for x in candidates if x['cms_slug']=='excursion-overview'},set(range(4)))
        self.assertEqual(len([x for x in candidates if x['cms_slug'].startswith('museum-exhibit-')]),6)
        self.assertEqual(len([x for x in candidates if x['cms_slug']=='building-history']),15)
        self.assertEqual({x['source_image_index'] for x in candidates if x['cms_slug']=='building-history'},set(range(15)))
        self.assertEqual(sum(x['source_image_index']==1 for x in candidates[:44]),17)

    def test_source_metadata_report_has_no_fabricated_assets(self):
        p=ROOT/'docs/source-migration/OFFICIAL_PHOTOS_IMPORTED_20261018.csv'
        with p.open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f,delimiter=';'))
        self.assertEqual(len(rows),199)
        self.assertEqual(len({r['original_url'] for r in rows}),len(rows))
        self.assertGreaterEqual(len({r['original_sha256'] for r in rows}),193)
        self.assertEqual(len({r['cms_slug'] for r in rows}),51)
        self.assertTrue(all(r['cms_slug'] in {x['cms_slug'] for x in cache.queue()} for r in rows))
        self.assertTrue(all(x['rights_status']=='private-needs-editorial-and-rights-review' for x in rows))
        self.assertTrue(all(re.fullmatch(r'[a-f0-9]{64}',x['original_sha256']) for x in rows))
        self.assertGreaterEqual(sum(int(x['source_image_index'])>0 for x in rows),80)
        self.assertTrue(all(x['original_url'].startswith('https://muzei-xleb.ru/sites/default/files/')
                            for x in rows))
        self.assertTrue(all('stock' not in x['original_url'] for x in rows))

    def test_cached_original_formats_only_real_jpeg_png_webp(self):
        self.assertEqual(cache.detect(b'\xff\xd8\xff'+b'\x00'*10+b'\xff\xd9'),'jpg')
        self.assertEqual(cache.detect(b'\x89PNG\r\n\x1a\n'+b'\x00'*10+b'IEND'),'png')
        self.assertEqual(cache.detect(b'RIFF'+b'\x00'*4+b'WEBP'+b'\x00'*12),'webp')
        with self.assertRaisesRegex(ValueError,'Image bytes'):
            cache.detect(b'<svg>Not a real JPEG photo</svg>')
        with self.assertRaisesRegex(ValueError,'Only original museum domain'):
            cache.canonical('https://example.com/photo.jpg')


if __name__=='__main__':
    unittest.main()
