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

    def test_corrupt_snapshot_rejected(self):
        self.snapshot.write_text("tampered")
        with self.assertRaises(ValueError):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)

    def test_export_symlink_rejected(self):
        (self.site / "unsafe").symlink_to(self.snapshot)
        with self.assertRaises(ValueError):
            rel.prepare(self.site, self.snapshot, self.manifest, self.dest)


if __name__ == "__main__":
    unittest.main()
