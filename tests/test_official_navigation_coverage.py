"""Source-menu snapshot coverage, not a legal rights or full media audit."""
from pathlib import Path
import csv,collections,unittest
ROOT=Path(__file__).resolve().parents[1]
class OfficialNavigationCoverageTests(unittest.TestCase):
    def test_original_menu_has_no_conjectured_nav_items(self):
        with (ROOT/'docs/source-migration/ORIGINAL_MENU_COVERAGE_20261018.csv').open(
            encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f,delimiter=';'))
        self.assertEqual(len(rows),41)
        self.assertEqual(len({x['path'] for x in rows}),41)
        self.assertTrue(all(x['original_url']=='https://muzei-xleb.ru'+x['path'] for x in rows))
        c=collections.Counter(x['status'] for x in rows)
        self.assertEqual(c['Исходный текст перенесён'],30)
        self.assertEqual(c['Исходный каталог перенесён'],8)
        self.assertEqual(c['Ссылка / отдельная проверка'],3)
        missing={x['path'] for x in rows if x['status']=='Ссылка / отдельная проверка'}
        self.assertEqual(missing,{
            '/covid-19','/gostevaya-kniga','/informaciya-dlya-dariteley',
        })
