"""Guard the grouped 325-clause delivery view against lost/misaligned rows."""
import csv
import json
import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'docs' / 'tz-audit'

class TzExecutionMatrixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (AUDIT / 'requirements.psv').open(encoding='utf-8') as f:
            cls.original = list(csv.DictReader(f, delimiter='^'))
        with (AUDIT / 'TZ_EXECUTION_MATRIX.csv').open(encoding='utf-8-sig') as f:
            cls.matrix = list(csv.DictReader(f, delimiter=';'))
        cls.viewer = (AUDIT / 'TZ_EXECUTION_MATRIX.html').read_text(encoding='utf-8')
        cls.markdown = (AUDIT / 'TZ_EXECUTION_MATRIX.md').read_text(encoding='utf-8')
        cls.bundle = json.loads((AUDIT / 'TZ_EXECUTION_MATRIX.json').read_text(encoding='utf-8'))

    def test_exactly_325_rows_same_order_and_text_as_primary_source(self):
        self.assertEqual(len(self.matrix), 325)
        self.assertEqual([r['ID ТЗ'] for r in self.matrix], [r['ID'] for r in self.original])
        self.assertEqual([r['Требование'] for r in self.matrix], [r['Атомарное обязательство'] for r in self.original])
        self.assertEqual([r['Пункт ТЗ'] for r in self.matrix], [r['Пункт ТЗ'] for r in self.original])
        self.assertEqual([r['Строки оригинала'] for r in self.matrix], [r['Строки tz.txt'] for r in self.original])
        self.assertEqual([r['Готовность'] for r in self.matrix], [r['Фактически готово'] for r in self.original])

    def test_current_wysiwyg_evidence_matches_installed_mit_editor(self):
        # Prevent stale historical TinyMCE claims from re-entering handoff.
        for tz in ('TZ-176', 'TZ-232', 'TZ-308', 'TZ-309'):
            row = next(r for r in self.original if r['ID'] == tz)
            self.assertIn('Jodit', row['Чекпоинт/доказательство'])
            self.assertNotIn('TinyMCE 7.2.1', row['Чекпоинт/доказательство'])

    def test_traffic_lights_and_nineteen_groups_are_complete(self):
        status = Counter(r['Готовность'] for r in self.matrix)
        self.assertEqual(status, Counter(r['Фактически готово'] for r in self.original))
        for row in self.matrix:
            expected = {'Да':'🟢 Готово','Частично':'🟡 Частично','Нет':'🔴 Не готово'}[row['Готовность']]
            self.assertEqual(row['Светофор'], expected)
            self.assertTrue(row['Группа'])
            self.assertIn(row['Приоритет'], ['P0','P1','P2'])
        self.assertEqual(len(set(row['Код группы'] for row in self.matrix)),19)

    def test_every_open_item_has_exactly_one_unblocked_queue_or_external_blocker(self):
        queue=[]
        for r in self.matrix:
            if r['Готовность']=='Да':
                self.assertFalse(r['№ очереди'])
                self.assertEqual(r['Режим'],'Готово в прототипе')
            elif r['№ очереди']:
                self.assertIn('очереди',r['Режим'])
                self.assertIn('#',r['Следующее действие / комментарий'])
                queue.append(int(r['№ очереди']))
            else:
                self.assertIn('Внешний блокер',r['Режим'])
                self.assertTrue(r['Что нужно от музея / внешний блокер'])
                self.assertTrue(r['Что сделать для завершения'])
        self.assertEqual(sorted(queue),list(range(1,len(queue)+1)))
        self.assertEqual(len(queue),sum(r['Режим'].startswith('В очереди') for r in self.matrix))
        self.assertEqual(sum('Внешний блокер' in r['Режим'] for r in self.matrix),
                         325-sum(r['Готовность']=='Да' for r in self.matrix)-len(queue))

    def test_json_markdown_html_all_cover_same_requirements(self):
        self.assertEqual(len(self.bundle['rows']),325)
        self.assertEqual([r['ID ТЗ'] for r in self.bundle['rows']],[r['ID ТЗ'] for r in self.matrix])
        for r in self.matrix:
            self.assertIn(r['ID ТЗ'],self.viewer)
            self.assertIn(r['ID ТЗ'],self.markdown)
        self.assertEqual(self.viewer.count('<tr data-group='),325)
        self.assertIn('матрица выполнения каждого пункта ТЗ',self.markdown)

    def test_checkpoint_notes_are_source_controlled_and_preserved(self):
        source=(AUDIT/'TZ_EXECUTION_MATRIX_CHECKPOINTS.md').read_text(encoding='utf-8').strip()
        self.assertGreaterEqual(source.count('> **'),4)
        self.assertIn('CODE-AUDIT-01',source)
        self.assertIn(source,self.markdown)

    def test_generator_is_deterministic(self):
        outputs=[AUDIT/f'TZ_EXECUTION_MATRIX.{extension}' for extension in ['csv','md','json','html']]
        before=[f.read_bytes() for f in outputs]
        subprocess.run([sys.executable,str(ROOT/'scripts/build_tz_execution_matrix.py')],check=True,capture_output=True)
        self.assertEqual([f.read_bytes() for f in outputs],before)

if __name__=='__main__':
    unittest.main()
