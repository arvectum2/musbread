"""Source-backed 61 literal Drupal /node links from genuine museum news."""
import hashlib,json,re,unittest
from pathlib import Path
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
class OriginalMuseumNodeExhibitionTests(unittest.TestCase):
    def test_all_61_historical_node_paths_have_source_verified_resolutions(self):
        d=json.loads((ROOT/'apps/web/src/data/official-node-linked-exhibitions.json').read_text())
        manifest=json.loads((ROOT/'.local_archive/news-linked-nodes/manifest.json').read_text())
        self.assertEqual(d['source'],'https://muzei-xleb.ru')
        self.assertEqual(d['node_count'],61)
        self.assertEqual(len(manifest['nodes']),61)
        self.assertEqual(d['verified_exhibition_node_count'],60)
        self.assertEqual(len(d['unavailable_nodes']),1)
        self.assertEqual(d['unavailable_nodes'][0]['path'],'/node/462')
        self.assertEqual(d['unavailable_nodes'][0]['status'],403)
        self.assertEqual(d['new_exhibition_count'],42)
        self.assertEqual(d['existing_exhibition_count'],18)
        self.assertEqual(len(d['exhibitions']),42)
        self.assertEqual(len({x['source_url'] for x in d['exhibitions']}),42)
        self.assertEqual(len({x['slug'] for x in d['exhibitions']}),42)

    def test_each_original_html_and_news_referer_has_digest_provenance(self):
        d=json.loads((ROOT/'apps/web/src/data/official-node-linked-exhibitions.json').read_text())
        museum=json.loads((ROOT/'apps/web/src/data/official-museum-news-archive.json').read_text())
        news={x['slug']:x for x in museum['articles']}
        for item in d['exhibitions']:
            with self.subTest(url=item['source_url']):
                self.assertRegex(item['source_url'],r'^https://muzei-xleb\.ru/vistavky/20\d{2}-\d\d-\d\d/[a-z0-9-]+$')
                self.assertEqual(item['category_slug'],'exhibitions-past')
                self.assertGreater(item['text_length'],8)
                self.assertEqual(hashlib.sha256(item['html'].encode()).hexdigest(),item['html_sha256'])
                self.assertFalse(item['photos_rights_confirmed'])
                original=(ROOT/'.local_archive/news-linked-nodes'/(item['node_path'].split('/')[-1]+'.html'))
                self.assertTrue(original.is_file())
                self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),item['source_page_sha256'])
                linking=news[item['linked_news_slug']]
                self.assertEqual(item['linked_news_html_sha256'],linking['html_sha256'])
                source_links=[a.get('href','') for a in html.fragment_fromstring(linking['html'],create_parent='div').xpath('.//a[@href]')]
                self.assertTrue(any(item['node_path']==__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(link).path for link in source_links))

if __name__=='__main__':unittest.main()
