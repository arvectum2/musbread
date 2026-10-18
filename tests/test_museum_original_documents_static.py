"""Original museum PDFs and DOCX must remain byte-identical after DNS cutover."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from export_official_museum_original_documents import export,source_documents,signature
class OriginalMuseumDocumentDomainCutoverTests(unittest.TestCase):
    def test_all_59_original_document_urls_map_to_exact_verified_bytes(self):
        docs=source_documents()
        self.assertEqual(len(docs),59)
        self.assertEqual(sum(x['format']=='pdf' for x in docs.values()),55)
        self.assertEqual(sum(x['format']=='docx' for x in docs.values()),4)
        self.assertGreater(sum(x['size_bytes'] for x in docs.values()),200_000_000)
        for path,item in docs.items():
            with self.subTest(path=path):
                self.assertTrue(path.startswith('/sites/default/files/'))
                archived=item['source_file']
                self.assertTrue(archived.is_file())
                self.assertEqual(signature(archived),item['sha256'])
                self.assertEqual(archived.stat().st_size,item['size_bytes'])
                public=ROOT/'apps/web/out'/path.lstrip('/')
                self.assertTrue(public.is_file())
                self.assertEqual(signature(public),item['sha256'])
                self.assertEqual(public.stat().st_size,item['size_bytes'])
    def test_archive_deployment_manifest_matches_unmodified_source_documents(self):
        manifest=json.loads((ROOT/'docs/source-migration/OFFICIAL_ORIGINAL_DOCUMENTS_DEPLOYMENT_20261018.json').read_text())
        self.assertEqual(manifest['count'],59)
        self.assertEqual(len(manifest['files']),59)
        self.assertEqual(len({x['legacy_path'] for x in manifest['files']}),59)
        self.assertNotIn('source_file',str(manifest))
        exported=export(verify_only=True)
        self.assertEqual(exported,manifest)
