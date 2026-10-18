"""Proof of 24 literal museum PDF/DOCX URLs found in old source-backed pages.

No borrowed/fake document; live-original HTTP 404 is recorded and excluded
from successful static delivery manifest.
"""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from cache_deeper_official_museum_documents import signed_docs
from export_official_museum_original_documents import source_documents

class DeepMuseumOriginalDocumentTests(unittest.TestCase):
 def test_twenty_four_explicit_old_original_document_urls_have_signed_source_html(self):
  docs=signed_docs()
  self.assertEqual(len(docs),24)
  self.assertEqual(len({x['url'] for x in docs.values()}),24)
  self.assertTrue(all(x['url'].startswith('https://muzei-xleb.ru/sites/default/files/page/') for x in docs.values()))

 def test_downloaded_originals_have_exact_source_bytes_and_missing_files_are_not_faked(self):
  originals=signed_docs()
  root=ROOT/'.local_archive/deep-original-documents'
  downloaded=json.loads((root/'manifest.json').read_text())
  unavailable=json.loads((root/'unavailable.json').read_text())
  self.assertEqual(downloaded['source'],'https://muzei-xleb.ru')
  self.assertEqual(downloaded['count']+unavailable['count'],24)
  source_paths={x['url'] for x in originals.values()}
  observed={x['url'] for x in downloaded['files']}|{x['url'] for x in unavailable['files']}
  self.assertEqual(source_paths,observed)
  self.assertEqual(len(observed),24)
  public=source_documents()
  for item in downloaded['files']:
   with self.subTest(url=item['url']):
    original=root/item['local_name']
    self.assertTrue(original.is_file())
    self.assertEqual(original.stat().st_size,item['size_bytes'])
    self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),item['sha256'])
    path=__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(item['url']).path
    self.assertIn(path,public)
    self.assertEqual(public[path]['sha256'],item['sha256'])
    deployed=ROOT/'apps/web/out'/path.lstrip('/')
    self.assertTrue(deployed.is_file())
    self.assertEqual(hashlib.sha256(deployed.read_bytes()).hexdigest(),item['sha256'])
  for missing in unavailable['files']:
   self.assertIn(missing['http_status'],(403,404,410))
   self.assertNotIn(__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(missing['url']).path,public)

if __name__=='__main__':unittest.main()
