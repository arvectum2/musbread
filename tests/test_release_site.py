import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

spec = spec_from_file_location("release_site", Path(__file__).resolve().parents[1] / "scripts/release_site.py")
assert spec and spec.loader
rel = module_from_spec(spec)
spec.loader.exec_module(rel)


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
        self.manifest.write_text(json.dumps({"files": {"published.json": {
            "sha256": hashlib.sha256(self.snapshot.read_bytes()).hexdigest(),
            "bytes": self.snapshot.stat().st_size,
        }}}))

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

    def test_history_reports_only_validated_local_releases_and_roles(self):
        first = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        (self.site / "index.html").write_text("version two")
        second = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        state = rel.history(self.dest)
        self.assertEqual(state["scope"], "LOCAL_PREAWARD_NOT_MUSEUM_PRODUCTION")
        self.assertEqual(state["current"], second)
        self.assertEqual(state["previous"], first)
        self.assertEqual(state["verified_release_count"], 2)
        self.assertEqual({r["role"] for r in state["releases"]}, {"current", "previous"})
        self.assertEqual(sum(r["file_count"] for r in state["releases"]), 2)
        self.assertTrue(all(r["total_bytes"] > 0 for r in state["releases"]))
        self.assertNotIn("private-snapshots", json.dumps(state))

    def test_history_rejects_corrupt_archived_version_and_invalid_pointer(self):
        first = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        (self.site / "index.html").write_text("version two")
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        (self.site / "index.html").write_text("version three")
        latest = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        before = (self.dest / "current").readlink()
        # Release one is archived (not current/previous) and still validated.
        (self.dest / "releases" / first / "index.html").write_text("modified")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            rel.history(self.dest)
        self.assertEqual((self.dest / "current").readlink(), before)
        (self.dest / "releases" / first / "index.html").write_text("version one")
        self.assertEqual(rel.history(self.dest)["current"], latest)
        (self.dest / "previous").unlink()
        (self.dest / "previous").symlink_to(Path("releases") / ("f"*16))
        with self.assertRaisesRegex(ValueError, "Invalid or unverified release pointer"):
            rel.history(self.dest)

    def test_history_fails_closed_on_unexpected_symlink_in_release_inventory(self):
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        (self.dest / "releases" / ("e"*16)).symlink_to(self.site, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Unexpected entry"):
            rel.history(self.dest)

    def test_private_archive_matches_release_and_never_enters_public_output(self):
        (self.site / "snapshot-manifest.json").write_bytes(self.manifest.read_bytes())
        version = rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        sha = hashlib.sha256(self.snapshot.read_bytes()).hexdigest()
        archived = self.dest / "private-snapshots" / (sha + ".json")
        self.assertEqual(archived.read_bytes(), self.snapshot.read_bytes())
        self.assertEqual(archived.stat().st_mode & 0o777, 0o600)
        self.assertEqual(rel.archive_current(self.dest, self.snapshot), sha)
        self.assertFalse((self.dest / "current/private-snapshots").exists())
        self.assertNotIn("private-snapshots", rel.files_with_hashes(self.dest / "current"))
        self.assertEqual(rel.validate_release((self.dest / "current").resolve()), version)
        self.snapshot.write_text('tampered')
        with self.assertRaisesRegex(ValueError, "differs from release snapshot manifest"):
            rel.archive_current(self.dest, self.snapshot)

    def test_private_archive_cannot_be_silently_overwritten(self):
        rel.prepare(self.site, self.snapshot, self.manifest, self.dest)
        sha = hashlib.sha256(self.snapshot.read_bytes()).hexdigest()
        private = self.dest / "private-snapshots" / (sha + ".json")
        private.write_bytes(b"MALICIOUS")
        with self.assertRaisesRegex(ValueError, "Private snapshot archive checksum mismatch"):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)

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
