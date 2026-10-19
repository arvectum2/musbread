import unittest
from pathlib import Path

from scripts.render_tz_audit import read_rows, ROOT


class OriginalTenderTraceTests(unittest.TestCase):
    def test_325_separately_scored_obligations(self):
        rows = read_rows()
        self.assertEqual(len(rows), 325)
        self.assertEqual([r['ID'] for r in rows], [f'TZ-{i:03d}' for i in range(1, 326)])

    def test_high_risk_omissions_not_misrepresented_as_ready(self):
        rows = {r['ID']: r for r in read_rows()}
        # 27 historical omissions now have explicit tasks and owners. Their
        # planning status improved, NOT their code-readiness status.
        for requirement in ('TZ-018', 'TZ-127'):
            self.assertEqual(rows[requirement]['Учли в плане'], 'Да')
            self.assertEqual(rows[requirement]['Фактически готово'], 'Нет')
        self.assertEqual(rows['TZ-124']['Фактически готово'], 'Да')
        self.assertIn('sigmapro',rows['TZ-124']['Чекпоинт/доказательство'])
        # TZ-189 was once a high-risk omission but has a real full-site link
        # title audit (incl. MoonShine-generated pages) and CI evidence.
        self.assertEqual(rows['TZ-189']['Учли в плане'], 'Да')
        self.assertEqual(rows['TZ-189']['Фактически готово'], 'Да')
        self.assertIn('MuseumLink/MuseumAnchor', rows['TZ-189']['Чекпоинт/доказательство'])
        # A prior omission may be genuinely closed during later development.
        self.assertEqual(rows['TZ-222']['Фактически готово'], 'Да')
        # Visitor manual is now a standalone draft, not an accepted final guide.
        self.assertEqual(rows['TZ-316']['Учли в плане'], 'Да')
        self.assertEqual(rows['TZ-316']['Фактически готово'], 'Частично')

        # Former omission now has a private demo-only workflow, not a live form.
        self.assertEqual(rows['TZ-085']['Учли в плане'], 'Да')
        self.assertEqual(rows['TZ-085']['Фактически готово'], 'Частично')
        self.assertEqual(rows['TZ-091']['Фактически готово'], 'Частично')
        # Client-only email-draft forms are now built and tested, but production
        # submissions, CMS ingestion and museum privacy approval are NOT done.
        for requirement in ('TZ-080','TZ-081','TZ-203','TZ-204','TZ-219'):
            self.assertEqual(rows[requirement]['Фактически готово'], 'Частично')
        self.assertIn('e-mail',rows['TZ-203']['Чекпоинт/доказательство'])
        self.assertIn('при необходимости',rows['TZ-219']['Чекпоинт/доказательство'])
        self.assertEqual(rows['TZ-283']['Фактически готово'], 'Нет')

    def test_original_structure_from_1_to_appendix_preserved(self):
        rows = read_rows()
        source_points = [r['Пункт ТЗ'] for r in rows]
        self.assertTrue(any('2.2.2.2' in p for p in source_points))
        self.assertTrue(any('2.2.3.6.1' in p for p in source_points))
        self.assertTrue(any('Раздел 5' in p for p in source_points))
        self.assertTrue(any('Приложение 1' in p for p in source_points))

    def test_final_csv_markdown_have_all_rows(self):
        full = (ROOT / 'docs/tz-audit/TZ_FULL_MATRIX.md').read_text(encoding='utf-8')
        for n in range(1, 326):
            self.assertIn(f'TZ-{n:03d}', full)
        self.assertIn('Учли?', full)
        self.assertIn('Готово?', full)
        self.assertIn('Нужно от заказчика', (ROOT / 'docs/tz-audit/requirements.psv').read_text())


if __name__ == '__main__':
    unittest.main()
