"""The site cannot be declared pre-award QA complete if Next build lost originals."""
import subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/build_complete_museum_static_release.py'
class MuseumCompleteStaticAssembleTests(unittest.TestCase):
 def test_complete_static_artifact_101_original_documents_259_photos_27_news_pages(self):
  completed=subprocess.run([sys.executable,str(SCRIPT),'--verify-only'],cwd=ROOT,capture_output=True,text=True,timeout=65)
  self.assertEqual(completed.returncode,0,completed.stdout[-750:]+completed.stderr[-900:])
  self.assertIn('MUSEUM_COMPLETE_LOCAL_ARTIFACT_PASS',completed.stdout)
  self.assertIn("'museum_PDF_DOCX_exact_sha256': 101",completed.stdout)
  self.assertIn("'museum_original_photo_source_URLs_selfhosted': 259",completed.stdout)
  self.assertIn("'source_verified_query_news_pages': 27",completed.stdout)
  self.assertIn("'prototype_robots_blocks_search': True",completed.stdout)
 def test_builder_is_opt_in_no_public_server_actions(self):
  src=SCRIPT.read_text()
  self.assertIn('mutually_exclusive_group(required=True)',src)
  self.assertIn('export_official_museum_original_documents.py',src)
  self.assertIn('export_official_museum_static_photos.py',src)
  self.assertIn('export_official_museum_news_pagination.py',src)
  self.assertIn('check_docs(verify_only=True)',src)
  self.assertIn('check_photos(DEFAULT_MAX_EDGE,True)',src)
  self.assertNotIn('ssh ',src)
  self.assertNotIn('git push',src)
  self.assertNotIn('S3',src)
if __name__=='__main__':unittest.main()
