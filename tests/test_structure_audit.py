import tempfile
import unittest
from pathlib import Path

from scripts.audit_structural_tz import audit


def html_doc(*, crumb: bool = True, social: bool = True) -> str:
    return (
        '<!doctype html><html><head><title>Test</title></head><body>'
        '<header class="site-header"></header>'
        '<main><nav aria-label="Хлебные крошки">' if crumb else
        '<!doctype html><html><head><title>Test</title></head><body>'
        '<header class="site-header"></header><main>'
    ) + (
        '<a href="/">Главная</a><span aria-current="page">Раздел</span></nav>'
        if crumb else ''
    ) + (
        '</main><footer class="site-footer">'
        '<a href="tel:+78122945082">Телефон</a>'
        '<a href="mailto:musbread@cult.gugov.spb.ru">Почта</a>'
        + ('<a href="https://vk.com/club37126776">VK</a>'
           '<a href="https://max.ru/id7808018523_gos">MAX</a>' if social else '')
        + '</footer></body></html>'
    )


class StructuralAuditTests(unittest.TestCase):
    def test_valid_home_and_inside_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'index.html').write_text(html_doc(crumb=False))
            (root/'news').mkdir()
            (root/'news/index.html').write_text(html_doc())
            actual=audit(root)
            self.assertEqual(actual['tested_visitor_pages'],2)
            self.assertTrue(actual['breadcrumbs_every_nonhome'])

    def test_missing_social_url_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'news').mkdir()
            (root/'news/index.html').write_text(html_doc(social=False))
            with self.assertRaisesRegex(AssertionError,'footer contact/social'):
                audit(root)

    def test_missing_breadcrumb_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'news').mkdir()
            (root/'news/index.html').write_text(html_doc(crumb=False))
            with self.assertRaisesRegex(AssertionError,'breadcrumbs'):
                audit(root)

    def test_verified_alias_fallback_is_not_misclassified_as_full_visitor_page(self):
        from scripts.build_museum_legacy_page_aliases import render_alias
        import csv
        manifest=Path(__file__).resolve().parents[1]/"docs/source-migration/LEGACY_MUSEUM_PAGE_ALIASES_20261018.csv"
        with manifest.open(encoding="utf-8-sig",newline="") as h:
            row=next(r for r in csv.DictReader(h,delimiter=";") if r["mode"].startswith("static-meta-refresh"))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/"index.html").write_text(html_doc(crumb=False))
            alias=root/row["legacy_path"].lstrip("/")/"index.html";alias.parent.mkdir(parents=True)
            alias.write_text(render_alias(row["legacy_path"],row["new_relative_url"]))
            result=audit(root)
            self.assertEqual(result["tested_visitor_pages"],1)
            self.assertEqual(result["verified_legacy_redirect_fallbacks"],1)
            alias.write_text(alias.read_text().replace("noindex","index"))
            with self.assertRaisesRegex(AssertionError,"fallback was modified"):
                audit(root)

    def test_en_sentinel_requires_noindex(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            sentinel=root/'en/museum/not-translated/index.html'
            sentinel.parent.mkdir(parents=True)
            sentinel.write_text('unpublished not-translated noindex')
            (root/'index.html').write_text(html_doc(crumb=False))
            self.assertEqual(audit(root)['safe_unpublished_EN_sentinels'],1)
            sentinel.write_text('not-translated yesindex')
            with self.assertRaisesRegex(AssertionError,'noindex'):
                audit(root)


if __name__ == '__main__':
    unittest.main()
