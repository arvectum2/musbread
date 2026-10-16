import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

_script = Path(__file__).resolve().parents[1] / "scripts/publish_snapshot.py"
_spec = spec_from_file_location("publish_snapshot", _script)
assert _spec is not None and _spec.loader is not None
pub = module_from_spec(_spec)
_spec.loader.exec_module(pub)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source, self.dest, self.manifest = root / "in.json", root / "out.json", root / "manifest.json"
        self.doc = {
            "schema_version": 1,
            "site": {"name": "Test", "subtitle": "Test", "description": "A site"},
            "events": [
                {"slug": "event-one", "title": "Title", "category": "Test",
                 "date": "2026-11-20", "excerpt": "Overview", "body": "Details"}
            ],
        }
        self.source.write_text(json.dumps(self.doc), encoding="utf-8")

    def test_deterministic_snapshot(self):
        pub.build(self.source, self.dest, self.manifest)
        original = self.dest.read_bytes()
        pub.build(self.source, self.dest, self.manifest, check=True)
        pub.build(self.source, self.dest, self.manifest)
        self.assertEqual(self.dest.read_bytes(), original)
        self.assertEqual(json.loads(self.manifest.read_text())["files"]["published.json"]["sha256"],
                         hashlib.sha256(original).hexdigest())

    def test_duplicate_slug_rejected(self):
        self.doc["events"].append(self.doc["events"][0].copy())
        self.source.write_text(json.dumps(self.doc), encoding="utf-8")
        with self.assertRaises(ValueError):
            pub.build(self.source, self.dest, self.manifest)

    def test_invalid_slug_rejected(self):
        self.doc["events"][0]["slug"] = "../etc"
        self.source.write_text(json.dumps(self.doc), encoding="utf-8")
        with self.assertRaises(ValueError):
            pub.build(self.source, self.dest, self.manifest)

    def test_unknown_content_type_rejected(self):
        self.doc["entries"] = [{"type": "script", "slug": "bad",
                                "title": "Wrong", "body": "Test"}]
        self.source.write_text(json.dumps(self.doc), encoding="utf-8")
        with self.assertRaises(ValueError):
            pub.build(self.source, self.dest, self.manifest)

    def test_duplicate_content_slug_rejected(self):
        item = {"type": "page", "slug": "duplicate", "title": "Page", "body": "Test"}
        self.doc["entries"] = [item, item.copy()]
        self.source.write_text(json.dumps(self.doc), encoding="utf-8")
        with self.assertRaises(ValueError):
            pub.build(self.source, self.dest, self.manifest)

    def test_modified_snapshot_detected(self):
        pub.build(self.source, self.dest, self.manifest)
        self.dest.write_text("{}")
        with self.assertRaises(SystemExit):
            pub.build(self.source, self.dest, self.manifest, check=True)


if __name__ == "__main__":
    unittest.main()
