import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_static_transfer import make_manifest, verify_manifest


class TransferIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.send = self.root / "sender"
        self.receive = self.root / "receiver"
        self.manifest = self.root / "trusted-inventory.json"
        self.send.mkdir()
        self.receive.mkdir()
        (self.send / "index.html").write_text("<h1>Verified CMS output</h1>")
        (self.send / "photo.webp").write_bytes(b"photo-asset")
        (self.receive / "index.html").write_bytes((self.send / "index.html").read_bytes())
        (self.receive / "photo.webp").write_bytes((self.send / "photo.webp").read_bytes())

    def test_roundtrip_rejects_tampered_missing_or_added_files(self):
        original = make_manifest(self.send, self.manifest)
        self.assertEqual(verify_manifest(self.receive, self.manifest), original)
        image = self.receive / "photo.webp"
        image.write_bytes(b"altered")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            verify_manifest(self.receive, self.manifest)
        image.write_bytes((self.send / "photo.webp").read_bytes())
        image.unlink()
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            verify_manifest(self.receive, self.manifest)
        image.write_bytes((self.send / "photo.webp").read_bytes())
        (self.receive / "extra.html").write_text("untrusted")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            verify_manifest(self.receive, self.manifest)

    def test_rejects_mutated_or_replaced_sidecar(self):
        make_manifest(self.send, self.manifest)
        with self.assertRaisesRegex(ValueError, "overwrite"):
            make_manifest(self.send, self.manifest)
        declared = json.loads(self.manifest.read_text())
        declared["sha256_of_canonical_inventory"] = "f"*64
        self.manifest.write_text(json.dumps(declared))
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            verify_manifest(self.receive, self.manifest)

    def test_manifest_must_be_outside_payload(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            make_manifest(self.send, self.send / "signed.json")

    def test_symlink_and_invalid_schema_fail_closed(self):
        make_manifest(self.send, self.manifest)
        (self.receive / "photo.webp").unlink()
        (self.receive / "photo.webp").symlink_to(self.send / "photo.webp")
        with self.assertRaisesRegex(ValueError, "Symlinks"):
            verify_manifest(self.receive, self.manifest)
        (self.receive / "photo.webp").unlink()
        (self.receive / "photo.webp").write_bytes((self.send / "photo.webp").read_bytes())
        self.manifest.write_text("{}")
        with self.assertRaisesRegex(ValueError, "schema"):
            verify_manifest(self.receive, self.manifest)


if __name__ == "__main__":
    unittest.main()
