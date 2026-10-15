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
        for requirement in ('TZ-018', 'TZ-124', 'TZ-127',
                            'TZ-189'):
            self.assertEqual(rows[requirement]['Учли в плане'], 'Нет')
            self.assertEqual(rows[requirement]['Фактически готово'], 'Нет')
        # A prior omission may be genuinely closed during later development.
        self.assertEqual(rows['TZ-222']['Фактически готово'], 'Да')
        # Visitor manual is now a standalone draft, not an accepted final guide.
        self.assertEqual(rows['TZ-316']['Учли в плане'], 'Частично')
        self.assertEqual(rows['TZ-316']['Фактически готово'], 'Частично')

        # Former omission now has a private demo-only workflow, not a live form.
        self.assertEqual(rows['TZ-085']['Учли в плане'], 'Нет')
        self.assertEqual(rows['TZ-085']['Фактически готово'], 'Частично')
        self.assertEqual(rows['TZ-091']['Фактически готово'], 'Частично')
        self.assertEqual(rows['TZ-080']['Фактически готово'], 'Нет')
        self.assertEqual(rows['TZ-081']['Фактически готово'], 'Нет')
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
