import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.handoff_bundle import Item, payload, create, verify, validate_source


class HandoffBundleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.archive = Path(temp.name) / "demo.zip"
        self.items = [
            Item("apps/web/src/app/page.tsx", b"export default function Page() {return null;}"),
            Item("docs/REQUIREMENTS.md", "Тестовые требования".encode("utf-8")),
        ]

    def make_archive(self, items=None):
        create(self.archive, payload("abc123", items or self.items))

    def test_archive_roundtrip_includes_manifests(self):
        self.make_archive()
        self.assertEqual(verify(self.archive), {"source_files": 2, "package_files": 7})
        with zipfile.ZipFile(self.archive) as z:
            self.assertIn("source/docs/REQUIREMENTS.md", z.namelist())
            self.assertIn(b"NOT_CREATED", z.read("STATUS.json"))
            self.assertIn(b"TARGET_CATALOG_ONLY_NO_MUSEUM_APPROVAL", z.read("STATUS.json"))
            self.assertIn(b"NOT_OWNED_NOT_TRANSFERABLE_AS_OWN_WORK", z.read("STATUS.json"))
            self.assertIn(b"INCOMPLETE_TECHNICAL_EXAMPLES_ONLY", z.read("STATUS.json"))
            self.assertIn(b"exclusive_rights_transferred", z.read("MANIFEST.json"))

    def test_reproducible_byte_for_byte(self):
        self.make_archive()
        original = self.archive.read_bytes()
        self.make_archive(list(reversed(self.items)))
        self.assertEqual(self.archive.read_bytes(), original)

    def test_changed_source_after_signing_detected(self):
        self.make_archive()
        with zipfile.ZipFile(self.archive) as z:
            content = {n: z.read(n) for n in z.namelist()}
        content["source/docs/REQUIREMENTS.md"] = b"changed"
        create(self.archive, content)
        with self.assertRaisesRegex(ValueError, "SHA256SUMS"):
            verify(self.archive)

    def test_traversal_is_rejected_on_build_and_verify(self):
        with self.assertRaisesRegex(ValueError, "Disallowed"):
            payload("abc123", [Item("../../.env", b"secret")])
        self.make_archive()
        with zipfile.ZipFile(self.archive) as z:
            content = {n: z.read(n) for n in z.namelist()}
        content["../escape.txt"] = b"escape"
        create(self.archive, content)
        with self.assertRaisesRegex(ValueError, "Unsafe ZIP"):
            verify(self.archive)

    def test_private_file_or_tracked_key_is_not_accepted(self):
        for name, contents in [
            ("apps/cms/.env", b"APP_KEY=whatever"),
            ("apps/cms/database/database.sqlite", b"SQLite format 3"),
            ("apps/cms/private.pem", b"any"),
            ("apps/web/src/secret.txt", b"-----BEGIN PRIVATE KEY-----\nsecret"),
            ("apps/web/src/token.txt", b"ghp_" + b"x" * 35),
        ]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_source(Item(name, contents))

    def test_placeholder_config_is_allowed_but_real_key_in_env_example_is_not(self):
        validate_source(Item("apps/cms/.env.example", b"APP_KEY=\nDB_PASSWORD=\n"))
        with self.assertRaisesRegex(ValueError, "Credential"):
            validate_source(Item("apps/cms/.env.example", b"APP_KEY=base64:abc"))

    def test_lying_about_rights_is_rejected(self):
        self.make_archive()
        with zipfile.ZipFile(self.archive) as z:
            content = {n: z.read(n) for n in z.namelist()}
        content["MANIFEST.json"] = content["MANIFEST.json"].replace(
            b'"exclusive_rights_transferred": false', b'"exclusive_rights_transferred": true'
        )
        # Repair outer sums so the violation is detected by semantic validation,
        # rather than the unimportant checksum order.
        from scripts.handoff_bundle import checksum
        content["SHA256SUMS"] = "".join(
            checksum(content[name]) + "  " + name + "\n"
            for name in sorted(content) if name != "SHA256SUMS"
        ).encode()
        create(self.archive, content)
        with self.assertRaisesRegex(ValueError, "Unjustified"):
            verify(self.archive)

    def test_duplicate_zip_member_is_rejected(self):
        with zipfile.ZipFile(self.archive, "w") as z:
            z.writestr("README_FIRST.md", "first")
            z.writestr("README_FIRST.md", "second")
        with self.assertRaisesRegex(ValueError, "Duplicate ZIP"):
            verify(self.archive)


if __name__ == "__main__":
    unittest.main()
