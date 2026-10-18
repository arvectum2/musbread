"""Verify 124 session dates/hours from six exact signed museum weekly news sources."""
import unittest,json,hashlib,re
from collections import Counter
from datetime import date,timedelta
from pathlib import Path
from lxml import html

ROOT=Path(__file__).resolve().parents[1]
class OfficialDatedSessionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'apps/web/src/data/official-agenda-sessions.json').read_text())
        cls.news=json.loads((ROOT/'apps/web/src/data/official-museum-news.json').read_text())
    def test_deduplicated_valid_museum_sessions(self):
        d=self.data
        self.assertEqual((d['original_bulletin_count'],d['raw_rows'],d['unique_sessions']),(6,140,124))
        self.assertEqual(len(d['sessions']),124)
        self.assertEqual(Counter(x['category'] for x in d['sessions']),{
            'Экскурсия':100,'Мастер-класс':15,'Интерактивное занятие':4,
            'Тематическая программа':3,'Литературная гостиная':2})
        self.assertEqual(len({x['slug'] for x in d['sessions']}),124)
        self.assertEqual(sum(len(x['source_urls'])-1 for x in d['sessions']),16)
    def test_each_day_and_time_is_explicit_in_original_news_bulletin(self):
        bulletins={x['source_url']:x for x in self.news['articles'] if x['title'].startswith('События в музее с ')}
        self.assertEqual(len(bulletins),6)
        for s in self.data['sessions']:
            with self.subTest(s=s['slug']):
                self.assertRegex(s['slug'],r'^museum-session-2026-(09|10)-\d\d-\d{4}-[a-f0-9]{12}$')
                self.assertTrue(re.fullmatch(r'\d{2}:\d{2} [^\n]+ \(\d+\+\)',s['original_row']))
                self.assertEqual(len(s['source_urls']),len(s['source_html_sha256']))
                self.assertEqual(len(s['source_urls']),len(s['source_rows']))
                for url,sha,raw_row in zip(s['source_urls'],s['source_html_sha256'],s['source_rows']):
                    b=bulletins[url]
                    self.assertEqual(sha,hashlib.sha256(b['html'].encode()).hexdigest())
                    publication=date.fromisoformat(b['published_on'])
                    day=date.fromisoformat(s['date'])
                    self.assertTrue(publication<=day<=publication+timedelta(days=8))
                    dom=html.fromstring('<div>'+b['html']+'</div>')
                    self.assertIn(raw_row,[' '.join(el.text_content().split()) for el in dom.xpath('.//li')])
                    self.assertIn(str(day.day)+' '+('сентября' if day.month==9 else 'октября'),
                        [' '.join(el.text_content().split()) for el in dom.xpath('.//p')])
    def test_archive_and_immediate_programmes_do_not_invent_end_times(self):
        sessions=self.data['sessions']
        self.assertEqual(sum(s['date']<'2026-10-18' for s in sessions),119)
        self.assertEqual(sum(s['date']>='2026-10-18' for s in sessions),5)
        self.assertEqual(sum(s['date']=='2026-10-18' for s in sessions),3)
        self.assertEqual(sum(s['date']=='2026-10-19' for s in sessions),2)
        for s in sessions:
            self.assertNotIn('end_time',s)
            self.assertNotIn('ticket_price',s)
            self.assertNotIn('available_seats',s)
            self.assertIn(s['time'],s['original_row'])
