"""No invented old museum source, no silent photo/PDF or index-file loss."""
from __future__ import annotations
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_museum_original_crosslinks import collect
from migrate_verified_news_index_media import go
from cache_verified_crosslink_documents import proven

class NewSourceFirstMuseumSectionsTests(unittest.TestCase):
    def test_all_37_original_section_pages_are_bound_to_verified_museum_html(self):
        doc=json.loads((ROOT/'apps/web/src/data/official-original-legacy-sections.json').read_text())
        self.assertEqual(doc['count'],37)
        self.assertEqual(doc['missing_originals'],[])
        self.assertEqual(len({x['path'] for x in doc['sections']}),37)
        for x in doc['sections']:
            with self.subTest(path=x['path']):
                self.assertEqual(hashlib.sha256(x['html'].encode()).hexdigest(),x['html_sha256'])
                self.assertEqual(x['source_url'],'https://muzei-xleb.ru'+x['path'])
                self.assertTrue((ROOT/'apps/web/out'/x['path'].lstrip('/')/'index.html').is_file())
                rendered=(ROOT/'apps/web/out'/x['path'].lstrip('/')/'index.html').read_text()
                self.assertIn('data-original-museum-section=',rendered)
                self.assertIn(f'href="{x["source_url"]}"',rendered)
                self.assertNotIn('http-equiv="refresh"',rendered)

    def test_six_newly_downloaded_page_html_bytes_match_preserved_private_originals(self):
        doc=json.loads((ROOT/'apps/web/src/data/official-remaining-original-sections.json').read_text())
        original=ROOT/'.local_archive/remaining-museum-original-section-html'
        self.assertEqual(doc['count'],6)
        for x in doc['pages']:
            with self.subTest(path=x['path']):
                f=original/(x['path'].lstrip('/')+'.html')
                self.assertTrue(f.is_file())
                self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(),x['source_page_sha256'])
                self.assertEqual(hashlib.sha256(x['html'].encode()).hexdigest(),x['html_sha256'])

    def test_fifteen_additional_museum_pages_and_ten_original_drupal_redirects_are_verified(self):
        d=json.loads((ROOT/'apps/web/src/data/official-museum-crosslink-pages.json').read_text())
        self.assertEqual(d['count'],15)
        self.assertEqual(len(d['redirects']),10)
        self.assertEqual(len(d['unavailable']),2)
        self.assertEqual({x['path'] for x in d['unavailable']},{'/node/462','/obratnaya-svyaz'})
        private=ROOT/'.local_archive/museum-crosslink-original-pages'
        for page in d['pages']:
            with self.subTest(path=page['path']):
                self.assertEqual(hashlib.sha256(page['html'].encode()).hexdigest(),page['html_sha256'])
                raw=private/(page['original_entry_path'].lstrip('/').replace('/','__')+'.html')
                self.assertTrue(raw.is_file())
                self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(),page['source_html_sha256'])
                rendered=ROOT/'apps/web/out'/page['path'].lstrip('/')/'index.html'
                self.assertTrue(rendered.is_file())
                self.assertIn('data-original-museum-section=',rendered.read_text())
        self.assertTrue(all(x['original_server_redirect_proven'] is True for x in d['redirects']))

    def test_all_ten_news_index_source_images_are_owned_and_checksum_verified(self):
        news=go(verify_only=True)
        self.assertEqual(news['count'],10)
        self.assertEqual(len({x['path'] for x in news['photos'].values()}),10)
        for img in news['photos'].values():
            public=ROOT/'apps/web/out'/img['path'].lstrip('/')
            self.assertTrue(public.is_file())
            self.assertEqual(hashlib.sha256(public.read_bytes()).hexdigest(),img['static_sha256'])

    def test_all_three_newly_discovered_original_documents_are_source_proven(self):
        proven_originals=proven()
        self.assertEqual(len(proven_originals),3)
        manifest=json.loads((ROOT/'.local_archive/extra-original-documents/manifest.json').read_text())
        self.assertEqual(manifest['count'],2)
        self.assertEqual(len(json.loads((ROOT/'.local_archive/extra-original-documents/unavailable.json').read_text())['files']),1)

    def test_additional_source_backed_internal_links_are_never_silently_marked_complete(self):
        summary=collect()
        self.assertGreaterEqual(summary['uncovered_unique_paths'],2)
        self.assertGreaterEqual(summary['unique_path_targets'],300)

if __name__=='__main__':unittest.main()
