import tempfile
import unittest
from pathlib import Path

from scripts.audit_public_artifacts import audit


class ArtifactAuditTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / "index.html").write_text("<h1>Public</h1>", encoding="utf-8")

    def test_simple_static_export_passes(self):
        (self.root / "museum").mkdir()
        (self.root / "museum/index.html").write_text("Museum", encoding="utf-8")
        self.assertEqual(audit(self.root)["files_checked"], 2)

    def test_private_database_file_is_rejected(self):
        (self.root / "database").mkdir()
        (self.root / "database/database.sqlite").write_bytes(b"SQLite format")
        with self.assertRaisesRegex(ValueError, "Private directory"):
            audit(self.root)

    def test_env_file_is_rejected(self):
        (self.root / ".env.local").write_text("FOO=bar")
        with self.assertRaisesRegex(ValueError, "Private directory"):
            audit(self.root)

    def test_javascript_secret_is_rejected(self):
        (self.root / "payload.js").write_bytes(b'const config="DB_PASSWORD=example";')
        with self.assertRaisesRegex(ValueError, "Secret-like"):
            audit(self.root)

    def test_symlink_is_rejected(self):
        (self.root / "linked.html").symlink_to(self.root / "index.html")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            audit(self.root)


if __name__ == "__main__":
    unittest.main()
