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
        self.assertGreaterEqual(len(candidates),55)
        self.assertEqual(len({x['original_url'] for x in candidates}),len(candidates))
        self.assertTrue(all(x['original_url'].startswith('https://muzei-xleb.ru/sites/default/files/')
                            for x in candidates))
        self.assertTrue(all(x['source_page_url'].startswith('https://muzei-xleb.ru/')
                            for x in candidates))
        self.assertEqual(sum(x['source_image_index']==0 for x in candidates),27)
        self.assertEqual(sum(x['source_image_index']==1 for x in candidates[:44]),17)

    def test_source_metadata_report_has_no_fabricated_assets(self):
        p=ROOT/'docs/source-migration/OFFICIAL_PHOTOS_IMPORTED_20261018.csv'
        with p.open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f,delimiter=';'))
        self.assertEqual((len(rows),len({r['cms_slug'] for r in rows}),
            len({r['original_sha256'] for r in rows})),(44,27,43))
        self.assertTrue(all(x['rights_status']=='private-needs-editorial-and-rights-review' for x in rows))
        self.assertTrue(all(re.fullmatch(r'[a-f0-9]{64}',x['original_sha256']) for x in rows))
        self.assertEqual(sum(int(x['source_image_index'])>0 for x in rows),17)
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
