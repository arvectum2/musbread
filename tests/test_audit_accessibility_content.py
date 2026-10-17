import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.audit_accessibility_content import audit, scan_page, report_md


HTML = '''<!DOCTYPE html>
<html lang="ru"><head><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Контроль качества музея</title></head>
<body><a href="#main">Перейти к содержимому</a><main id="main">
<h1>Документы</h1><p>Вымышленный тестовый текст</p></main></body></html>'''


class StaticContentAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "index.html").write_text(HTML, encoding="utf8")

    def test_valid_html_has_no_errors(self):
        result = audit(self.root)
        self.assertEqual(result["summary"]["errors"], 0)
        self.assertEqual(result["summary"]["html_pages"], 1)
        self.assertIn("NOT ГОСТ/PDF-UA compliance", report_md(result))

    def test_missing_alt_and_wrong_language_are_detected(self):
        bad = HTML.replace('lang="ru"', 'lang="en"').replace(
            "<h1>Документы</h1>", '<h1>Документы</h1><img src="/media/photo.webp">')
        (self.root / "index.html").write_text(bad)
        result = audit(self.root)
        codes = {row["code"] for row in result["errors"]}
        self.assertIn("LANG_MISMATCH", codes)
        self.assertIn("IMG_MISSING_ALT", codes)

    def test_unlabelled_field_duplicate_id_and_missing_skip_are_detected(self):
        bad = HTML.replace('<a href="#main">Перейти к содержимому</a>', '')
        bad = bad.replace("<h1>Документы</h1>", '<h1 id="main">Документы</h1><input id="test">')
        (self.root / "index.html").write_text(bad)
        result = audit(self.root)
        codes = {row["code"] for row in result["errors"]}
        self.assertTrue({"SKIP_LINK", "DUPLICATE_ID", "UNLABELLED_FIELD"}.issubset(codes))

    def test_exported_document_is_verified_and_unreviewed_is_warning_not_pass(self):
        data = b"entirely synthetic PDF binary data"
        sha = hashlib.sha256(data).hexdigest()
        relative = f"/documents/{sha}.pdf"
        folder = self.root / "documents"
        folder.mkdir()
        (folder / f"{sha}.pdf").write_bytes(data)
        snapshot = self.root / "snapshot.json"
        import json
        snapshot.write_text(json.dumps({
            "entries": [{
                "slug": "demo", "documents": [{
                    "href": relative, "format": "pdf", "accessibility_reviewed": False,
                    "accessibility_note": None
                }]
            }]
        }))
        result = audit(self.root, snapshot)
        self.assertEqual(result["summary"]["errors"], 0)
        self.assertEqual(result["summary"]["documents"], 1)
        self.assertEqual(
            {x["code"] for x in result["warnings"]},
            {"DOCUMENT_UNREVIEWED", "PDF_UA_UNVERIFIED"})
        strict = audit(self.root, snapshot, strict_documents=True)
        self.assertEqual(strict["summary"]["errors"], 2)
        (folder / f"{sha}.pdf").write_bytes(b"tampered")
        result = audit(self.root, snapshot)
        self.assertIn("DOCUMENT_CHECKSUM", {x["code"] for x in result["errors"]})

    def test_unreviewed_private_note_rejected_and_review_without_note_rejected(self):
        import json
        data = b"test XLSX data"
        sha = hashlib.sha256(data).hexdigest()
        (self.root / "documents").mkdir()
        (self.root / "documents" / f"{sha}.xlsx").write_bytes(data)
        snapshot = self.root / "snapshot.json"
        item = {"href": f"/documents/{sha}.xlsx", "format": "xlsx",
                "accessibility_reviewed": False, "accessibility_note": "private draft"}
        snapshot.write_text(json.dumps({"entries": [{"slug": "test", "documents": [item]}]}))
        result = audit(self.root, snapshot)
        self.assertIn("DOCUMENT_PRIVATE_NOTE", {x["code"] for x in result["errors"]})
        item["accessibility_reviewed"] = True
        item["accessibility_note"] = "short"
        snapshot.write_text(json.dumps({"entries": [{"slug": "test", "documents": [item]}]}))
        result = audit(self.root, snapshot)
        self.assertIn("DOCUMENT_NOTE_MISSING", {x["code"] for x in result["errors"]})

    def test_published_image_without_alt_and_incomplete_english_are_rejected(self):
        import json
        snapshot = self.root / "snapshot.json"
        snapshot.write_text(json.dumps({"entries": [
            {"slug": "ex", "media": [{"src": "/media/safe.webp", "alt": ""}],
             "translations": {"en": {"title": "English", "body": ""}}}
        ]}))
        result = audit(self.root, snapshot)
        codes = {x["code"] for x in result["errors"]}
        self.assertIn("CMS_IMAGE_ALT", codes)
        self.assertIn("EN_TRANSLATION_INCOMPLETE", codes)

    def test_cms_media_alt_and_extended_description_policy_fail_closed(self):
        import json
        snapshot = self.root / "snapshot.json"
        for value in ["Фотография экспоната", "Рисунок фото в музее", "А" * 126]:
            snapshot.write_text(json.dumps({"entries": [{"slug": "test", "media": [{
                "src": "/media/dummy.webp", "alt": value
            }]}]}, ensure_ascii=False))
            result = audit(self.root, snapshot)
            self.assertIn("CMS_IMAGE_ALT_POLICY", {x["code"] for x in result["errors"]})
        snapshot.write_text(json.dumps({"entries": [{"slug": "test", "media": [{
            "src": "/media/dummy.webp", "alt": "Кирпичная печь на стенде",
            "long_description": "Схема печи с тремя отверстиями и дверцей."
        }]}]}, ensure_ascii=False))
        result = audit(self.root, snapshot)
        self.assertNotIn("CMS_IMAGE_ALT_POLICY", {x["code"] for x in result["errors"]})
        self.assertNotIn("CMS_IMAGE_LONG_DESC", {x["code"] for x in result["errors"]})
        bad = HTML.replace("<h1>Документы</h1>", '<h1>Документы</h1><img alt="Фото зала" src="/media/test.webp">')
        (self.root / "index.html").write_text(bad)
        self.assertIn("ALT_POLICY", {x["code"] for x in audit(self.root)["errors"]})

    def test_sentinel_must_be_noindex(self):
        folder = self.root / "en/museum/not-translated"
        folder.mkdir(parents=True)
        html = folder / "index.html"
        html.write_text("<html><head><meta name='robots' content='noindex'></head></html>")
        result = audit(self.root)
        self.assertEqual(result["summary"]["errors"], 0)
        html.write_text("<html><body>Error</body></html>")
        result = audit(self.root)
        self.assertIn("SENTINEL_INDEXABLE", {x["code"] for x in result["errors"]})


if __name__ == "__main__":
    unittest.main()
