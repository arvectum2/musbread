"""CP-34D: whole locked package universe, graph and copyright limitations."""
import copy
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.build_dependency_sbom import (
    ROOT, REQUIRED, bom, license_risk, npm_resolve, report, write_or_check,
)


class LockedSbomTests(unittest.TestCase):
    def test_entire_locked_universe_and_direct_dependency_graph(self):
        cyclo, details, missing, count = bom()
        c = json.loads((ROOT/"apps/cms/composer.lock").read_text())
        n = json.loads((ROOT/"apps/web/package-lock.json").read_text())
        self.assertEqual(count["composer"],len(c["packages"]))
        self.assertEqual(count["composer-dev"],len(c["packages-dev"]))
        self.assertEqual(count["npm"],len(n["packages"])-1)
        self.assertEqual(len(cyclo["components"]),560)
        self.assertEqual(cyclo["bomFormat"],"CycloneDX")
        self.assertEqual(cyclo["specVersion"],"1.6")
        self.assertEqual(len(cyclo["dependencies"]),561)
        refs={i["bom-ref"] for i in cyclo["components"]}
        self.assertEqual(len(refs),len(cyclo["components"]))
        self.assertIn("embedded:tinymce-runtime",refs)
        self.assertIn("native:librsvg",refs)
        self.assertEqual({i["class"] for i in missing},{"optional_or_peer"})
        self.assertEqual(len(missing),4)
        for r in cyclo["dependencies"]:
            self.assertTrue(set(r["dependsOn"])<=refs)
        rootdeps=next(i["dependsOn"] for i in cyclo["dependencies"]
                      if i["ref"]=="musbread:source-project")
        self.assertIn("npm:node_modules/next",rootdeps)
        self.assertTrue(any(x.startswith("composer:laravel/framework@") for x in rootdeps))
        self.assertIn("embedded:tinymce-runtime",rootdeps)
        self.assertIn("native:librsvg",rootdeps)

    def test_license_risks_and_conditional_platforms_kept(self):
        document, details, missing, count = bom()
        names={i["name"]:i for i in document["components"]}
        self.assertIn("GPL-2.0-or-later",
                      [x["license"]["name"] for x in names["TinyMCE bundled editor runtime"]["licenses"]])
        self.assertEqual(details["npm:node_modules/@img/sharp-libvips-darwin-arm64"]["risk"],
                         "WEAK_COPYLEFT_LGPL")
        self.assertTrue(details["npm:node_modules/@img/sharp-libvips-darwin-arm64"]["optional"])
        self.assertEqual(details["npm:node_modules/@playwright/test"]["scope"],"development")
        self.assertEqual(details["composer:ezyang/htmlpurifier@v4.19.1"]["risk"],
                         "WEAK_COPYLEFT_LGPL")
        self.assertEqual(license_risk("MIT"),"PERMISSIVE_NOTICE_CHECK")
        self.assertEqual(license_risk("MPL-2.0"),"FILE_LEVEL_COPYLEFT_REVIEW")
        self.assertEqual(license_risk("UNVERIFIED"),"UNKNOWN_REQUIRES_VERIFICATION")

    def test_reproducible_generated_cdx_and_csv_and_no_clearance_claim(self):
        document, summary, licenses=report()
        stats=json.loads(summary)
        self.assertFalse(stats["legal_clearance"])
        self.assertFalse(stats["transferred_exclusive_third_party_rights"])
        self.assertGreaterEqual(len(list(csv.DictReader(licenses.splitlines()))),560)
        self.assertEqual(document["components"],report()[0]["components"])
        self.assertEqual(write_or_check(ROOT,True)["total_components"],560)

    def test_changing_an_entire_locked_package_or_its_license_fails_report_gate(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            for item in REQUIRED:
                p=root/item;p.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(ROOT/item,p)
            p=root/"apps/web/package-lock.json"
            data=json.loads(p.read_text())
            data["packages"]["node_modules/next"]["license"]="GPL-3.0-only"
            p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"Missing/stale"):
                write_or_check(root,True)

    def test_missing_root_direct_lock_package_fails_closed(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)
            for item in REQUIRED:
                p=root/item;p.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(ROOT/item,p)
            p=root/"apps/web/package-lock.json"
            obj=json.loads(p.read_text())
            del obj["packages"]["node_modules/react"]
            p.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError,"Missing npm root direct dependency"):
                bom(root)

    def test_node_nested_and_scope_resolution(self):
        paths={"node_modules/@scope/pkg","node_modules/alpha",
               "node_modules/alpha/node_modules/beta","node_modules/beta"}
        self.assertEqual(npm_resolve("node_modules/alpha","beta",paths),
                         "node_modules/alpha/node_modules/beta")
        self.assertEqual(npm_resolve("node_modules/alpha","@scope/pkg",paths),
                         "node_modules/@scope/pkg")
        self.assertIsNone(npm_resolve("node_modules/alpha","missing",paths))
        with self.assertRaises(ValueError):
            npm_resolve("node_modules/alpha","../secret",paths)


if __name__=="__main__":
    unittest.main()
