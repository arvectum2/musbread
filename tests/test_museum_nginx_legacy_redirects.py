"""Production-ready, but unapplied, Nginx redirection coverage checks."""
from pathlib import Path
from urllib.parse import urlsplit
import json,sys,re,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_museum_nginx_legacy_redirects import render
from build_museum_legacy_page_aliases import build_map
class MuseumNginxCutoverTests(unittest.TestCase):
    def test_original_museum_pages_and_webp_sources_receive_only_safe_local_301_destinations(self):
        stats=render()
        self.assertGreaterEqual(stats['total'],664)
        self.assertEqual(stats['page'],368)  # 280 technical URLs + 88 source-verified original Drupal /node links
        data=json.loads((ROOT/'apps/web/src/data/official-museum-photo-assets.json').read_text())
        self.assertEqual(stats['photo_original'],data['count'])
        self.assertEqual(stats['news_index_original_photos'],10)
        self.assertEqual(stats['deep_original_photos'],37)
        self.assertEqual(stats['historical_exhibition_photos'],4)
        conf=(ROOT/'deploy/nginx/legacy_museum_redirects.map.conf').read_text()
        self.assertTrue(conf.startswith('# GENERATED FROM source-verified'))
        self.assertIn('map $uri $musbread_legacy_target {',conf)
        self.assertIn('    default "";',conf)
        self.assertNotIn('muzei-xleb.ru ',conf)
        # Double-quotes are REQUIRED around targets with #fragment: unquoted
        # Nginx '#' starts a comment, losing the target fragment.
        match=re.findall(r'^    (/\S+) "([^"\s]+)";$',conf,re.M)
        self.assertEqual(len(match),stats['total'])
        parsed=dict(match)
        self.assertEqual(len(parsed),len(match))
        self.assertNotIn('/novosty',parsed)  # Original index now has its own canonical HTML 200
        for old,item in build_map().items():
            if item['why']=='original-news-article':
                self.assertNotIn(old,parsed)
                self.assertEqual(parsed[item['target'].rstrip('/')],old)
            elif item['why']=='source-verified-drupal-node':
                self.assertEqual(parsed[old],item['target'])
            else:
                # 467 source original article/section/program URLs now serve
                # their own real HTML and must NOT redirect to catalogue anchors.
                self.assertNotIn(old,parsed)
        for original,photo in data['photos'].items():
            for source in (original,photo['source_image_url']):
                self.assertEqual(parsed[urlsplit(source).path],photo['path'])
                self.assertTrue((ROOT/'apps/web/public'/photo['path'].removeprefix('/')).is_file())
        self.assertTrue(all('#' not in value for value in parsed.values()))
        index=json.loads((ROOT/'apps/web/src/data/official-news-index-photo-assets.json').read_text())
        self.assertEqual(index['count'],10)
        for original,asset in index['photos'].items():
            self.assertEqual(parsed[urlsplit(original).path],asset['path'])
            self.assertTrue((ROOT/'apps/web/public'/asset['path'].removeprefix('/')).is_file())
        tea=json.loads((ROOT/'apps/web/src/data/official-historical-exhibition-image-assets.json').read_text())
        self.assertEqual(tea['count'],4)
        for old,asset in tea['photos'].items():
            self.assertEqual(parsed[urlsplit(old).path],asset['path'])
            self.assertTrue((ROOT/'apps/web/public'/asset['path'].lstrip('/')).is_file())
        for old,target in match:
            self.assertTrue(old.startswith('/'))
            self.assertTrue(target.startswith('/'))
            self.assertNotEqual(old,urlsplit(target).path.rstrip('/'))
        host=(ROOT/'deploy/nginx/legacy_museum_redirects.server.conf').read_text()
        self.assertIn('return 301 $musbread_legacy_target;',host)
        self.assertNotIn('rewrite',host)

if __name__=='__main__':unittest.main()
