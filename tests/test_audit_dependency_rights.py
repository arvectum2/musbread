import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.audit_dependency_rights import ROOT, audit, markdown


class DependencyRightsTests(unittest.TestCase):
    def test_locked_evidence_does_not_claim_exclusive_vendor_rights(self):
        # CI source-only jobs intentionally have no Composer vendor directory.
        # Locked dependency/license checks are always required; physical
        # installed-asset checks run separately on machines with vendor.
        obj=audit(ROOT)
        self.assertFalse(obj["all_licenses_legally_cleared"])
        self.assertFalse(obj["contract_ready"])
        self.assertFalse(obj["third_party_exclusive_rights_transfer"])
        self.assertEqual(obj["summary"]["embedded_gpl_bundles"],0)
        self.assertEqual(obj["summary"]["direct_php"],3)
        self.assertEqual(obj["summary"]["direct_web"],4)
        self.assertGreaterEqual(obj["summary"]["license_review_blockers"],6)
        self.assertTrue(all(not x["redistributed_upstream_code_owned_by_arvectum"] for x in obj["entries"]))
        self.assertFalse(any("tinymce" in x["name"] for x in obj["entries"]))
        runtime=next(x for x in obj["entries"] if x["name"]=="jodit/community-runtime")
        self.assertEqual(runtime["declared_licenses"],["MIT"])
        self.assertIn("jodit",markdown(obj).lower())

    def test_dependency_version_and_license_are_taken_from_locks(self):
        data=audit(ROOT)
        cm=json.loads((ROOT/"apps/cms/composer.lock").read_text())
        c={x["name"]:x for x in cm["packages"]}
        npm=json.loads((ROOT/"apps/web/package-lock.json").read_text())["packages"]
        for line in data["entries"]:
            if line["ecosystem"]=="composer":
                self.assertEqual(line["version"],c[line["name"]]["version"])
                self.assertEqual(line["declared_licenses"],c[line["name"]]["license"])
            if line["ecosystem"]=="npm":
                x=npm["node_modules/"+line["name"]]
                self.assertEqual(line["version"],x["version"])
                self.assertEqual(line["declared_licenses"],[x["license"]])

    def test_missing_lock_dependency_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for item in ("apps/cms/composer.lock","apps/cms/composer.json",
                         "apps/web/package-lock.json","apps/web/package.json",
                         "scripts/requirements-design-tools.txt"):
                target=root/item
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(ROOT/item,target)
            path=root/"apps/cms/composer.lock"
            obj=json.loads(path.read_text())
            obj["packages"]=[x for x in obj["packages"] if x["name"]!="moonshine/moonshine"]
            path.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError,"Missing required direct PHP"):
                audit(root)

    def test_changed_python_pin_must_trigger_reassessment(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for item in ("apps/cms/composer.lock","apps/cms/composer.json",
                         "apps/web/package-lock.json","apps/web/package.json",
                         "scripts/requirements-design-tools.txt"):
                target=root/item
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(ROOT/item,target)
            path=root/"scripts/requirements-design-tools.txt"
            path.write_text("python-pptx==2.0.0\npypdf==5.6.1\n")
            with self.assertRaisesRegex(ValueError,"pin changed"):
                audit(root)

    def test_vendor_license_mismatch_must_not_be_silenced(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for item in ("apps/cms/composer.lock","apps/cms/composer.json",
                         "apps/web/package-lock.json","apps/web/package.json",
                         "scripts/requirements-design-tools.txt"):
                target=root/item;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(ROOT/item,target)
            p=root/"apps/cms/public/vendor/museum-jodit/LICENSE.txt"
            p.parent.mkdir(parents=True)
            p.write_text("License: unknown, different copyright holder")
            with self.assertRaisesRegex(ValueError,"MIT notice changed"):
                audit(root,check_vendor=True)


if __name__=="__main__":
    unittest.main()
