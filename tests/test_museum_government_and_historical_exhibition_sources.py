"""Original government assignment PDF and historic tea-gallery source preservation."""
from __future__ import annotations
import hashlib,json,sys,unittest
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from cache_government_official_museum_documents import signed_docs
from cache_historical_museum_exhibition_images import verified_urls
from export_official_museum_original_documents import source_documents

class DeepLegalAndTeaMuseumSourceTests(unittest.TestCase):
 def test_twenty_original_museum_government_pdf_urls_from_real_source_html(self):
  referenced=signed_docs()
  self.assertEqual(len(referenced),20)
  data=ROOT/'.local_archive/government-original-documents'
  saved=json.loads((data/'manifest.json').read_text())
  broken=json.loads((data/'unavailable.json').read_text())
  self.assertEqual(saved['count'],19)
  self.assertEqual(broken['count'],1)
  self.assertEqual(broken['files'][0]['http_status'],404)
  self.assertTrue(broken['files'][0]['url'].endswith('/202110271242-prikaz_no94.pdf'))
  self.assertEqual({r['url'] for r in referenced.values()},
      {r['url'] for r in saved['files']}|{r['url'] for r in broken['files']})
  originals=source_documents()
  self.assertEqual(len(originals),101)
  for item in saved['files']:
   with self.subTest(url=item['url']):
    old=urlsplit(item['url']).path
    raw=(data/item['local_name']).read_bytes()
    self.assertTrue(raw.startswith(b'%PDF'))
    self.assertEqual(hashlib.sha256(raw).hexdigest(),item['sha256'])
    self.assertEqual(len(raw),item['size_bytes'])
    self.assertEqual(originals[old]['sha256'],item['sha256'])
    public=ROOT/'apps/web/out'/old.lstrip('/')
    self.assertTrue(public.is_file())
    self.assertEqual(hashlib.sha256(public.read_bytes()).hexdigest(),item['sha256'])
  self.assertNotIn(urlsplit(broken['files'][0]['url']).path,originals)

 def test_four_actual_archived_museum_exhibition_photos_and_gallery_are_local(self):
  image_sources=verified_urls()
  self.assertEqual(len(image_sources),4)
  saved=json.loads((ROOT/'apps/web/src/data/official-historical-exhibition-image-assets.json').read_text())
  self.assertEqual(saved['count'],4)
  self.assertEqual(saved['unavailable'],[])
  self.assertEqual(set(saved['photos']),{ref['original_url'] for ref in image_sources.values()})
  exhibition=json.loads((ROOT/'apps/web/src/data/official-deep-museum-pages.json').read_text())
  galleries=[x for x in exhibition['pages'] if x['path'].startswith('/vistavky/2019-06-21/')]
  self.assertEqual(len(galleries),1)
  self.assertEqual(len(galleries[0]['image_links']),4)
  self.assertEqual({x['url'] for x in galleries[0]['image_links']},set(saved['photos']))
  for old,record in saved['photos'].items():
   with self.subTest(url=old):
    raw=ROOT/'.local_archive/historical-exhibition-original-images'/(record['original_sha256']+'.'+record['original_format'])
    webp=ROOT/'apps/web/out'/record['path'].lstrip('/')
    self.assertTrue(raw.is_file())
    self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(),record['original_sha256'])
    self.assertTrue(webp.is_file())
    self.assertEqual(hashlib.sha256(webp.read_bytes()).hexdigest(),record['static_sha256'])
  exhibit=ROOT/'apps/web/out'/galleries[0]['path'].lstrip('/')/'index.html'
  self.assertTrue(exhibit.is_file())
  page=exhibit.read_text()
  self.assertIn('data-original-museum-exhibition=',page)
  self.assertIn('https://muzei-xleb.ru'+galleries[0]['path'],page)
  self.assertNotIn('http-equiv="refresh"',page)

 def test_deep_old_museum_articles_are_source_hash_locked_and_unavailable_statuses_are_not_faked(self):
  m=json.loads((ROOT/'apps/web/src/data/official-deep-museum-pages.json').read_text())
  self.assertEqual(m['count'],19)
  self.assertEqual(len(m['redirects']),18)
  self.assertEqual({p['path'] for p in m['unavailable']},{'/node/462','/obratnaya-svyaz'})
  self.assertEqual({p['http_status'] for p in m['unavailable']},{403})
  for page in m['pages']:
   with self.subTest(page=page['path']):
    self.assertEqual(hashlib.sha256(page['html'].encode()).hexdigest(),page['html_sha256'])
    local=ROOT/'.local_archive/deep-original-museum-pages'/(page['original_entry_path'].lstrip('/').replace('/','__')+'.html')
    self.assertEqual(hashlib.sha256(local.read_bytes()).hexdigest(),page['source_html_sha256'])
    public=ROOT/'apps/web/out'/page['path'].lstrip('/')/'index.html'
    self.assertTrue(public.is_file())
    self.assertIn('href="'+page['source_url']+'"',public.read_text())

if __name__=='__main__':unittest.main()
