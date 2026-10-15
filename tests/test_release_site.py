import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from importlib.machinery import SourceFileLoader

rel = SourceFileLoader("release_site", str(Path(__file__).resolve().parents[1] / "scripts/release_site.py")).load_module()


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        root = Path(self.dir.name)
        self.site, self.dest = root / "site", root / "deploy"
        self.snapshot, self.manifest = root / "content.json", root / "manifest.json"
        self.site.mkdir()
        (self.site / "index.html").write_text("version one")
        self.snapshot.write_bytes(b'{"events":[]}\n')
        self.manifest.write_text(json.dumps({"files": {"published.json": {"sha256": hashlib.sha256(self.snapshot.read_bytes()).hexdigest()}}}))

    def test_release_and_rollback(self):
        a = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        self.assertEqual((self.dest / "current/index.html").read_text(), "version one")
        self.assertEqual(rel.prepare(self.site, self.snapshot, self.manifest, self.dest), a)
        (self.site / "index.html").write_text("version two")
        b = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        self.assertNotEqual(a, b)
        self.assertEqual((self.dest / "current/index.html").read_text(), "version two")
        self.assertEqual(rel.rollback(self.dest), a)
        self.assertEqual((self.dest / "current/index.html").read_text(), "version one")

    def test_existing_release_manifest_corruption_prevents_redeployment(self):
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        active = (self.dest / "current").resolve()
        manifest = active / "release-manifest.json"
        doc = json.loads(manifest.read_text())
        doc["release"] = "evil-mismatched-id"
        manifest.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)

    def test_corrupted_previous_release_cannot_be_rolled_back(self):
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        (self.site / "index.html").write_text("version two")
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        before = (self.dest / "current").readlink()
        previous = (self.dest / "previous").resolve()
        (previous / "index.html").write_text("TAMPERED")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            rel.rollback(self.dest)
        self.assertEqual((self.dest / "current").readlink(), before)

    def test_current_release_verification_rejects_tampering(self):
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        active = (self.dest / "current").resolve()
        self.assertTrue(rel.validate_release(active))
        (active / "index.html").write_text("altered")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            rel.validate_release(active)

    def test_corrupt_snapshot_rejected(self):
        self.snapshot.write_text("tampered")
        with self.assertRaises(ValueError):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)

    def test_tampered_media_asset_rejected_before_release_switch(self):
        media = self.site / "media"
        media.mkdir()
        item = media / ("a" * 64 + ".webp")
        item.write_bytes(b"safe-public-webp-test")
        meta = json.loads(self.manifest.read_text())
        meta["files"]["media/" + item.name] = {
            "sha256": hashlib.sha256(item.read_bytes()).hexdigest(),
            "bytes": item.stat().st_size,
        }
        self.manifest.write_text(json.dumps(meta))
        release_id = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        self.assertEqual((self.dest / "current/media" / item.name).read_bytes(), item.read_bytes())
        self.assertTrue(release_id)
        item.write_bytes(b"altered-after-export")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)

    def test_missing_media_asset_rejected(self):
        meta = json.loads(self.manifest.read_text())
        meta["files"]["media/" + "b" * 64 + ".webp"] = {"sha256": "b" * 64, "bytes": 8}
        self.manifest.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, "Missing or unsafe"):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)

    def test_document_export_is_verified_and_tamper_blocks_release(self):
        directory = self.site / "documents"
        directory.mkdir()
        name = hashlib.sha256(b"office-fixture").hexdigest() + ".docx"
        document = directory / name
        document.write_bytes(b"office-fixture")
        meta = json.loads(self.manifest.read_text())
        meta["files"]["documents/" + name] = {
            "sha256": hashlib.sha256(document.read_bytes()).hexdigest(),
            "bytes": document.stat().st_size,
        }
        self.manifest.write_text(json.dumps(meta))
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        document.write_bytes(b"MODIFIED")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)

    def test_unexpected_document_filename_is_rejected(self):
        meta = json.loads(self.manifest.read_text())
        meta["files"]["documents/../../bad.pdf"] = {"sha256": "b" * 64, "bytes": 10}
        self.manifest.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, "Unexpected asset path"):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)

    def test_export_symlink_rejected(self):
        (self.site / "unsafe").symlink_to(self.snapshot)
        with self.assertRaises(ValueError):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)


if __name__ == "__main__":
    unittest.main()
