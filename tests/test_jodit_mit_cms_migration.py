"""Regression gate for the MIT Jodit WYSIWYG, lock + runtime deliverables."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'apps/cms/public/vendor/museum-jodit'
SHA={
 'LICENSE.txt':'b6eccb41553c575c01f6a1261e87fdc7b842a721d6ba9daa88bdbd9259865d55',
 'jodit.min.js':'d65fd78a72e6acfdae4cb0f47fef3c90f72ff8b40d5043313b49c4757db62008',
 'jodit.min.css':'4195186166912468e2a361c6be27d42f5b78b7487fb54f14155ca83d3a6e9035',
}
class JoditMITMigrationTests(unittest.TestCase):
 def test_pinned_selfhosted_actual_npm_assets_and_mit_notice(self):
  for fname,digest in SHA.items():
   self.assertTrue((ASSETS/fname).is_file(),fname)
   self.assertEqual(hashlib.sha256((ASSETS/fname).read_bytes()).hexdigest(),digest)
  lic=(ASSETS/'LICENSE.txt').read_text()
  self.assertIn('Permission is hereby granted, free of charge',lic)
  self.assertIn('Copyright (c) 2013-2026 https://xdsoft.net',lic)
 def test_no_tinymce_package_or_public_runtime_in_supported_release(self):
  p=ROOT/'apps/cms'
  package=json.loads((p/'composer.json').read_text())
  lock=json.loads((p/'composer.lock').read_text())
  self.assertNotIn('moonshine/tinymce',package['require'])
  self.assertNotIn('moonshine/tinymce',[x['name'] for x in lock['packages']])
  self.assertFalse((p/'public/vendor/moonshine-tinymce').exists())
  self.assertFalse((p/'vendor/moonshine/tinymce').exists())
  fields=(p/'app/MoonShine/Resources/MuseumEntry/Pages/MuseumEntryFormPage.php').read_text()
  self.assertIn("'jodit' => Jodit::make",fields)
  self.assertNotIn('TinyMce::make(',fields)
  self.assertIn("'entry_body_editor' => env('MUSEUM_ENTRY_BODY_EDITOR', 'jodit')",(p/'config/museum.php').read_text())
 def test_private_cms_nginx_serves_only_mit_editor_js_css_not_license_or_php(self):
  nginx=(ROOT/'infra/nginx/private-cms.conf').read_text()
  self.assertIn('moonshine|museum-jodit',nginx)
  self.assertNotIn('moonshine-tinymce',nginx)
  self.assertIn('location ~ ^/(storage|database|bootstrap|vendor)/ { return 404; }',nginx)
 def test_init_has_no_cdn_upload_or_pii_submission_and_server_sanitizer_stays_in_place(self):
  init=(ASSETS/'museum-jodit-init.js').read_text()
  self.assertIn('window.Jodit.make(element',init)
  self.assertIn('insertImageAsBase64URI: false',init)
  self.assertIn("'formdata'",init)
  self.assertNotIn('fetch(',init)
  self.assertNotIn('tiny.cloud',init)
  self.assertIn('MuseumHtmlSanitizer', (ROOT/'apps/cms/app/Models/MuseumEntry.php').read_text())
if __name__=='__main__':unittest.main()
