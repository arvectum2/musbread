"""Historical /novosti original JPGs must be verified against real museum source HTML."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from cache_deeper_official_museum_images import verified_urls,run

class DeepMuseumOriginalMediaTests(unittest.TestCase):
 def test_all_thirty_seven_jpeg_links_are_signed_by_the_real_museum_html(self):
  refs=verified_urls()
  self.assertEqual(len(refs),37)
  self.assertTrue(all(x['original_url'].startswith('https://muzei-xleb.ru/sites/default/files/page/') for x in refs.values()))
  self.assertTrue(all(x['source_page_url']=='https://muzei-xleb.ru/novosti' for x in refs.values()))

 def test_all_original_media_are_locally_source_owned_not_linked_to_old_hosting(self):
  refs=verified_urls()
  d=json.loads((ROOT/'apps/web/src/data/official-deep-news-image-assets.json').read_text())
  self.assertEqual(d['count']+len(d['unavailable']),37)
  self.assertEqual(set(x['original_url'] for x in refs.values()),set(d['photos'])|{x['original_url'] for x in d['unavailable']})
  source=ROOT/'.local_archive/deep-original-images'
  public=ROOT/'apps/web/public'
  for url,r in d['photos'].items():
   with self.subTest(url=url):
    raw=source/(r['original_sha256']+'.'+r['original_format'])
    webp=public/r['path'].lstrip('/')
    self.assertTrue(raw.is_file())
    self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(),r['original_sha256'])
    self.assertEqual(raw.stat().st_size,r['original_bytes'])
    self.assertTrue(webp.is_file())
    self.assertEqual(hashlib.sha256(webp.read_bytes()).hexdigest(),r['static_sha256'])
    self.assertTrue(r['path'].startswith('/media/museum-source/'))
  for unavailable in d['unavailable']:
   self.assertIn(unavailable['http_status'],(403,404,410))

 def test_repeat_verification_of_original_sha_and_self_hosted_webp_is_idempotent(self):
  run(limit=37,verify_only=True)

if __name__=='__main__':unittest.main()
