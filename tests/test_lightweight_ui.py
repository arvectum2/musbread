import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("museum_lightweight_ui",ROOT/"scripts/audit_lightweight_ui.py")
module=importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class TestStaticLightweightUI(unittest.TestCase):
    def fixture(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        p=Path(tmp.name)
        (p/"index.html").write_text(
            '<html><head><script defer src="/_next/static/chunks/app.js"></script></head>'
            '<body><main><img src="/media/approved.webp" alt="Разрешённая фотография" loading="lazy"></main></body></html>',
            encoding="utf-8")
        (p/"_next/static/chunks").mkdir(parents=True)
        (p/"_next/static/chunks/app.js").write_bytes(b"const a=1;")
        return p

    def test_current_public_snapshot_has_no_remote_scripts_embeds_or_heavy_assets(self):
        output=ROOT/"apps/web/out"
        if not output.is_dir():
            self.skipTest("Public static site must be built before full audit")
        report=module.audit(output)
        self.assertEqual(report["status"],"PASS",report["issues"][:8])
        self.assertGreaterEqual(report["html_pages"],20)
        self.assertLessEqual(report["js_bytes_total"],module.MAX_JS_TOTAL)

    def test_clean_small_local_static_assets_are_accepted(self):
        p=self.fixture()
        self.assertEqual(module.audit(p)["status"],"PASS")

    def test_remote_js_embeds_and_autoplay_are_rejected(self):
        p=self.fixture()
        (p/"index.html").write_text(
            '<script src="https://tracker.invalid/sdk.js"></script>'
            '<iframe src="/third-party"></iframe>'
            '<video autoplay controls src="/media/untitled.mp4"></video>'
            '<link rel="preload" as="video" href="/media/untitled.mp4">',
            encoding="utf-8")
        issues=module.audit(p)["issues"]
        self.assertTrue(any("External script" in x for x in issues))
        self.assertTrue(any("Embedded" in x for x in issues))
        self.assertTrue(any("Autoplay" in x for x in issues))
        self.assertTrue(any("Preloaded video" in x for x in issues))

    def test_oversized_chunk_is_not_silently_accepted(self):
        p=self.fixture()
        (p/"_next/static/chunks/app.js").write_bytes(b"a"*(module.MAX_JS_CHUNK+1))
        self.assertEqual(module.audit(p)["status"],"FAIL")

    def test_externalized_content_stays_within_per_page_budget(self):
        p=self.fixture()
        directory=p/"_next/static/musbread-inline"
        directory.mkdir(parents=True)
        excessive="a.js"
        (directory/excessive).write_bytes(b"x"*(module.MAX_HYDRATION_ASSET+1))
        (p/"index.html").write_text(
            '<script src="/_next/static/musbread-inline/a.js"></script>',encoding="utf-8")
        result=module.audit(p)
        self.assertEqual(result["status"],"FAIL")
        self.assertTrue(any("Oversized page hydration content asset" in x
                            for x in result["issues"]))
        self.assertTrue(any("Oversized per-page React data transfer" in x
                            for x in result["issues"]))

    def test_media_size_limit_and_symlink_are_enforced(self):
        p=self.fixture()
        (p/"media").mkdir()
        (p/"media/image.webp").write_bytes(b"x"*(module.MAX_MEDIA_FILE+1))
        self.assertEqual(module.audit(p)["status"],"FAIL")
        (p/"media/image.webp").unlink()
        (p/"media/image.webp").symlink_to(p/"_next/static/chunks/app.js")
        self.assertEqual(module.audit(p)["status"],"FAIL")


if __name__=="__main__":
    unittest.main()
