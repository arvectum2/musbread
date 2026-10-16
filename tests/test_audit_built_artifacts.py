"""CP-35D exact installed file inventory, license warnings and source-only ZIP."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_built_artifacts import (
    ROOT, cms_report, collect, sha_file, web_report, zip_report,
)
from scripts.handoff_bundle import Item, create, payload, source_allowed


class BuiltArtifactTests(unittest.TestCase):
    def test_local_compiled_public_export_and_local_vendor_are_real(self):
        # This test only performs full environment checks where those generated
        # paths exist; CI has separate mandatory checks after npm/composer install.
        web=ROOT/"apps/web/out"
        if web.is_dir():
            data=web_report(web)
            self.assertGreaterEqual(data["files_total"],80)
            self.assertGreater(data["compiled_js_css_count"],0)
            self.assertEqual(data["bundled_third_party_component_map"],
                             "NOT_ESTABLISHED_FROM_MINIFIED_JS")
            self.assertFalse(data["external_binary_license_approved"])
        cms=ROOT/"apps/cms/public"
        vendor=ROOT/"apps/cms/vendor"
        if (vendor/"composer/installed.json").is_file() and (cms/"vendor/moonshine-tinymce/license.md").is_file():
            data=cms_report(cms,vendor,ROOT/"apps/cms/composer.lock")
            self.assertEqual(data["embedded_tinymce_version"],"7.2.1")
            self.assertEqual(data["tiny_mce_removal_status"],"STILL_INSTALLED")
            self.assertGreater(data["installed_vendor_files"],1000)
            self.assertGreater(data["public_vendor_count"],100)
            self.assertTrue(any("Gilroy-" in x["path"] for x in data["font_license_blockers"]))
            self.assertFalse(data["museum_production_delivery"])

    def test_reject_unexpected_file_and_symlinks_on_public_export(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            (root/"_next/static/chunks").mkdir(parents=True)
            (root/"index.html").write_text("<html><body>test</body></html>")
            js=root/"_next/static/chunks/app.js"
            js.write_text("console.log('demo')")
            self.assertEqual(web_report(root)["compiled_js_css_count"],1)
            (root/"secret.php").write_text("<?php echo 123;")
            with self.assertRaises(ValueError):
                web_report(root)
            (root/"secret.php").unlink()
            (root/"injected.js").symlink_to(js)
            with self.assertRaisesRegex(ValueError,"Symlink"):
                web_report(root)

    def test_actual_cms_assets_and_installed_composer_version_matching(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            public=root/"public"
            vendor=root/"vendor"
            d=public/"vendor/moonshine"
            (d/"assets").mkdir(parents=True)
            (d/"assets/app.js").write_text("window.app=true")
            (d/"assets/main.css").write_text("body{margin:0}")
            tiny=public/"vendor/moonshine-tinymce"
            tiny.mkdir(parents=True)
            (tiny/"license.md").write_text("GNU General Public License Version 2 or later")
            (tiny/"tinymce.min.js").write_text("/** TinyMCE version 7.2.1 (2024-07-03) */\nwindow.tiny=1")
            (vendor/"composer").mkdir(parents=True)
            pkg=vendor/"example/package"
            pkg.mkdir(parents=True)
            (pkg/"run.php").write_text("<?php echo 1;")
            (vendor/"composer/installed.json").write_text(json.dumps(
                {"packages":[{"name":"example/package","version":"v1.0.0"}]}))
            lock=root/"composer.lock"
            lock.write_text(json.dumps({"packages":[
                {"name":"example/package","version":"v1.0.0","license":["MIT"]}],
                "packages-dev":[]}))
            report=cms_report(public,vendor,lock)
            self.assertEqual(report["public_vendor_count"],4)
            self.assertEqual(report["installed_package_count"],1)
            self.assertEqual(report["installed_vendor_files"],1)
            self.assertEqual(report["font_license_blockers"],[])
            # Unknown license change in the embedded JS must be explicit.
            (tiny/"license.md").write_text("MIT")
            with self.assertRaisesRegex(ValueError,"GPL notice"):
                cms_report(public,vendor,lock)
            (tiny/"license.md").write_text("GNU General Public License Version 2 or later")
            (vendor/"composer/installed.json").write_text(json.dumps(
                {"packages":[{"name":"example/package","version":"v1.0.1"}]}))
            with self.assertRaisesRegex(ValueError,"differs"):
                cms_report(public,vendor,lock)

    def test_source_demo_archive_excludes_vendor_and_compiled_site(self):
        with tempfile.TemporaryDirectory() as dirname:
            filename=Path(dirname)/"preaward.zip"
            items=[
                Item("README.md",b"pre-award sample"),
                Item("docs/handoff/SBOM_CYCLONEDX.json",b'{"status":"not-legal"}'),
            ]
            create(filename,payload("a"*40,items))
            obj=zip_report(filename)
            self.assertFalse(obj["vendor_or_build_assets_included"])
            self.assertTrue(obj["source_files"]>=2)
            self.assertTrue(obj["legal_rights"].startswith("PENDING"))
            for bad in ("apps/cms/vendor/moonshine/runtime.js",
                        "apps/web/out/_next/chunk.js",
                        "apps/web/node_modules/react/index.js",
                        "apps/cms/public/vendor/moonshine/assets/app.js"):
                self.assertFalse(source_allowed(bad))

    def test_hashes_change_on_modified_asset(self):
        with tempfile.TemporaryDirectory() as dirname:
            p=Path(dirname)/"tmp.js"
            p.write_bytes(b"A")
            h=sha_file(p)
            p.write_bytes(b"B")
            self.assertNotEqual(h,sha_file(p))


if __name__=="__main__":
    unittest.main()
