import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

path = Path(__file__).resolve().parents[1] / 'scripts/preflight_museum_release.py'
spec = spec_from_file_location('preflight_museum_release', path)
pre = module_from_spec(spec); spec.loader.exec_module(pre)


class PreflightTests(unittest.TestCase):
    def setUp(self):
        (pre.ROOT/'.local_archive').mkdir(parents=True, exist_ok=True)
        d = tempfile.TemporaryDirectory(dir=pre.ROOT/'.local_archive')
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        self.out = self.root / 'out'; self.out.mkdir()
        (self.out/'index.html').write_text('<html>Staging</html>')
        (self.out/'robots.txt').write_text('User-Agent: *\nDisallow: /\n')
        (self.out/'sitemap.xml').write_text('<urlset></urlset>')

    def test_staging_seo_passes_only_noindex(self):
        self.assertTrue(pre.verify_staging_seo(self.out)['robots_blocks'])
        (self.out/'robots.txt').write_text('Allow: /')
        with self.assertRaisesRegex(pre.PreflightError, 'robots'):
            pre.verify_staging_seo(self.out)

    def test_staging_sitemap_and_build_marker_fail_closed(self):
        (self.out/'sitemap.xml').write_text('<urlset><url>fake</url></urlset>')
        with self.assertRaisesRegex(pre.PreflightError, 'sitemap'):
            pre.verify_staging_seo(self.out)
        (self.out/'sitemap.xml').write_text('<urlset></urlset>')
        (self.out/'.musbread-legacy-alias').touch()
        with self.assertRaisesRegex(pre.PreflightError, 'marker'):
            pre.verify_staging_seo(self.out)

    def test_rollback_rehearsal_preserves_original_and_no_production(self):
        self.assertTrue(pre.rehearse_rollback(self.root)['prior_release_restored'])
        self.assertEqual(sorted(x.name for x in self.root.iterdir()), ['out'])

    def test_release_inventory_rejects_tampering(self):
        snap = self.root/'snapshot'; snap.write_bytes(b'{}')
        manifest = self.root/'manifest'; manifest.write_text(json.dumps({'files': {
            'published.json': {'sha256': hashlib.sha256(b'{}').hexdigest(), 'bytes': 2}}}))
        site = self.root/'site'; site.mkdir()
        dest = self.root/'dest'
        (site/'index.html').write_text('A')
        pre.releases.prepare(site, snap, manifest, dest)
        with self.assertRaisesRegex(pre.PreflightError, 'previous'):
            pre.verify_existing_release(dest)
        (site/'index.html').write_text('B')
        pre.releases.prepare(site, snap, manifest, dest)
        self.assertIn('previous', pre.verify_existing_release(dest))
        (dest/'current/index.html').write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            pre.verify_existing_release(dest)

    def test_nginx_static_barrier(self):
        conf = self.root/'static.conf'; conf.write_text('proxy_pass http://private;')
        with self.assertRaisesRegex(pre.PreflightError, 'Missing public Nginx'):
            pre.verify_nginx_template(conf)
        self.assertTrue(pre.verify_nginx_template(pre.ROOT/'infra/nginx/public-static.conf')['static_only'])

    def test_live_validation_rejects_staging_and_bad_redirects(self):
        base = 'https://example.org'
        answers = {'/': (200,b'<html>Site</html>',{'X-Content-Type-Options':'nosniff', 'Content-Security-Policy':"default-src 'self'", 'Strict-Transport-Security':'max-age=31536000'}),
            '/robots.txt': (200,b'User-Agent: *\nAllow: /',{}),
            '/sitemap.xml': (200,b'<url><loc>https://example.org/news/</loc></url>',{}),
            '/old/': (301,b'',{'Location':'/news/'})}
        def fake(url): return answers[url.removeprefix(base)]
        self.assertEqual(pre.verify_live_site(base,[('/old/','/news/')],fake)['redirect_samples'],1)
        answers['/robots.txt']=(200,b'User-Agent: *\nDisallow: /',{})
        with self.assertRaisesRegex(pre.PreflightError, 'robots'):
            pre.verify_live_site(base,[('/old/','/news/')],fake)
        answers['/robots.txt']=(200,b'User-Agent: *\nDisallow: /private\nAllow: /',{})
        answers['/old/']=(302,b'',{'Location':'/news/'})
        with self.assertRaisesRegex(pre.PreflightError, '301'):
            pre.verify_live_site(base,[('/old/','/news/')],fake)
        answers['/old/']=(301,b'',{'Location':'/news/'})
        answers['/']=(200,b'<html>Site</html>',{})
        with self.assertRaisesRegex(pre.PreflightError, 'Missing X-Content-Type'):
            pre.verify_live_site(base,[('/old/','/news/')],fake)
        with self.assertRaisesRegex(pre.PreflightError, 'Expected --live-url'):
            pre.verify_live_site('http://example.org',[],fake)


if __name__ == '__main__': unittest.main()
