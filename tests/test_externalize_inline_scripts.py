"""Real static Next.js inline JS is moved to exact-hash assets, never discarded."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from scripts.externalize_inline_scripts import externalize, transform
from scripts.build_csp import make_csp


class ExternalizedScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "_next/static/chunks").mkdir(parents=True)
        (self.root / "guide").mkdir()
        (self.root / "index.html").write_text(
            '<!doctype html><html><head><script id="__next_f">window.a=1;</script>'
            '<script src="/_next/static/chunks/f.js" async=""></script></head>'
            '<body><script>window.b=2;</script></body></html>', encoding="utf-8")
        (self.root / "guide/index.html").write_text(
            '<script>window.a=1;</script><script type="application/ld+json">{"@type":"Museum"}</script>',
            encoding="utf-8")

    def test_content_addressed_dedup_sri_and_short_strict_csp(self):
        report = externalize(self.root)
        self.assertEqual(report["html_pages"], 2)
        self.assertEqual(report["assets"], 2)  # identical code shared across two pages
        self.assertEqual(report["remaining_inline"], 0)
        html = (self.root / "index.html").read_text()
        self.assertIn('id="__next_f" src="/_next/static/musbread-inline/', html)
        self.assertIn('integrity="sha384-', html)
        self.assertIn('crossorigin="anonymous"', html)
        self.assertIn('<script src="/_next/static/chunks/f.js" async=""></script>', html)
        self.assertIn('type="application/ld+json"', (self.root / "guide/index.html").read_text())
        scripts=list((self.root / "_next/static/musbread-inline").glob("*.js"))
        for script in scripts:
            self.assertEqual(hashlib.sha256(script.read_bytes()).hexdigest(),script.stem)
        policy=make_csp(self.root)
        self.assertIn("script-src 'self';",policy)
        self.assertNotIn("'unsafe-eval'",policy)
        self.assertNotIn("script-src 'self' 'unsafe-inline'",policy)
        self.assertNotIn("'sha256-",policy)
        self.assertLess(len(policy.encode()),8192)
        self.assertEqual(report,externalize(self.root,verify_only=True))
        self.assertEqual(report,externalize(self.root))  # idempotent

    def test_script_tamper_and_lost_sri_fail_closed(self):
        externalize(self.root)
        js=next((self.root / "_next/static/musbread-inline").glob("*.js"))
        js.write_bytes(b"window.injected=1")
        with self.assertRaisesRegex(ValueError,"Modified externalized"):
            make_csp(self.root)

    def test_executable_script_drift_after_manifest_refused(self):
        externalize(self.root)
        p=self.root / "guide/index.html"
        p.write_text(p.read_text()+"<script>window.attack=1</script>")
        with self.assertRaisesRegex(ValueError,"Unexternalized inline"):
            externalize(self.root,verify_only=True)

    def test_sri_attribute_tamper_refused(self):
        externalize(self.root)
        p=self.root / "index.html"
        p.write_text(p.read_text().replace('sha384-', 'sha384-x',1))
        with self.assertRaisesRegex(ValueError,"SRI missing"):
            externalize(self.root,verify_only=True)

    def test_adjacent_flight_payloads_are_grouped_without_reordering(self):
        html = ('<script>(self.__next_f=self.__next_f||[]).push([0])</script>'
                '<script>self.__next_f.push([1,"first"])</script>'
                '<script>self.__next_f.push([1,"second"])</script>'
                '<div>content must remain in document position</div>'
                '<script>self.__next_f.push([1,"third"])</script>')
        built, files, n=transform(html)
        self.assertEqual(n,3)  # one bootstrap, one batch, one after markup
        self.assertEqual(built.count("/_next/static/musbread-inline/"),3)
        self.assertIn("<div>content must remain in document position</div>",built)
        bundles=[raw.decode() for raw in files.values()]
        self.assertTrue(any('first' in x and 'second' in x
                            and x.index('first')<x.index('second') for x in bundles))
        self.assertTrue(any('third' in x for x in bundles))

    def test_late_archive_html_is_only_allowed_manifest_count_difference(self):
        externalize(self.root)
        archive=self.root/"__museum_legacy_pager"
        archive.mkdir()
        for i in range(1,28):
            (archive/("page-"+str(i)+".html")).write_text("<main>Original museum archive</main>")
        result=externalize(self.root,verify_only=True)
        self.assertEqual(result["html_pages"],29)
        (self.root/"unexpected-route").mkdir()
        (self.root/"unexpected-route/index.html").write_text("<main>unexpected generated page</main>")
        with self.assertRaisesRegex(ValueError,"Stale/invalid"):
            externalize(self.root,verify_only=True)

    def test_html_transform_preserves_nonexecutable_data(self):
        html='<script type="application/ld+json">{"text":"abc"}</script><script>window.c=3;</script>'
        changed,assets,n=transform(html)
        self.assertEqual(n,1)
        self.assertEqual(len(assets),1)
        self.assertIn('{"text":"abc"}',changed)


if __name__=="__main__":
    unittest.main()
