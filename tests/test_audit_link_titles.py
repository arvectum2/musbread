import tempfile
import unittest
from pathlib import Path
from scripts.audit_link_titles import audit

class LinkTitleAuditTests(unittest.TestCase):
    def test_valid_title_present_for_contextual_and_external_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"index.html").write_text(
                '<main><a href="/events/" title="Открыть афишу">Афиша</a>'
                '<a href="https://example.org/" title="Внешний сайт">Источник</a></main>',
                encoding="utf-8")
            self.assertEqual(audit(root)["links"],2)
            self.assertEqual(audit(root)["pages_missing_link_titles"],0)

    def test_missing_and_whitespace_title_are_both_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"index.html").write_text(
                '<a href="/events/">Афиша</a><a href="mailto:a@example.org" title="  ">Почта</a>',
                encoding="utf-8")
            found=audit(root)
            self.assertEqual(found["links"],2)
            self.assertEqual(found["missing_titles"]["index.html"],
                             ["/events/","mailto:a@example.org"])

    def test_covers_nested_pages_and_skips_elements_without_href(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"index.html").write_text('<a>Без ссылки</a>',encoding="utf-8")
            (root/"events").mkdir()
            (root/"events/index.html").write_text('<a href="/news/">Новости</a>',encoding="utf-8")
            found=audit(root)
            self.assertEqual(found["links"],1)
            self.assertEqual(found["missing_titles"]["events/index.html"],["/news/"])

if __name__=="__main__":
    unittest.main()
