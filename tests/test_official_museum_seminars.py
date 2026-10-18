"""Seven real past scientific seminars from actual museum index /seminary."""
from __future__ import annotations
import json,re,hashlib,unittest
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[1]
PIN={
 '633':'2026-04-16','536':'2025-11-06','425':'2024-02-07',
 '361':'2023-04-05','291':'2022-04-14','271':'2021-11-10','189':'2020-11-10',
}
class ActualMuseumSeminarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.d=json.loads((ROOT/'apps/web/src/data/official-museum-seminars.json').read_text())
    def test_original_index_and_all_seven_dated_headings(self):
        d=self.d
        self.assertEqual((d['source'],d['index_url']),
          ('https://muzei-xleb.ru','https://muzei-xleb.ru/seminary'))
        self.assertEqual(d['index_html_sha256'],'d3317f19b3b1a78b1b8478e73205e74b57d8fafe6f2939cf13540a483cb6158e')
        self.assertEqual((d['count'],d['video_count']), (7,16))
        self.assertEqual(len({x['id'] for x in d['seminars']}),7)
        for item in d['seminars']:
            with self.subTest(id=item['id']):
                node=item['index_detail_path'].rsplit('/',1)[-1]
                self.assertIn(node,PIN)
                self.assertEqual(item['date_start'],PIN[node])
                self.assertEqual(item['id'],'science-seminar-'+item['date_start']+'-'+node)
                self.assertRegex(item['page_html_sha256'],r'^[0-9a-f]{64}$')
                self.assertTrue(item['title'].startswith('Семинар '))
                self.assertIn(item['date_start'][:4],item['title'])
                self.assertTrue(item['source_url'].startswith('https://muzei-xleb.ru/seminar-'))
                self.assertFalse(item['media_rehosted'])
                self.assertFalse(item['photo_rights_confirmed'])
                self.assertEqual(len(item['videos']),item['video_count'])
    def test_no_fake_seminar_dates_and_original_videos_only(self):
        d=self.d
        self.assertEqual([e['video_count'] for e in d['seminars']],[2,2,2,2,2,3,3])
        self.assertEqual(d['seminars'][-1]['date_end'],'2020-11-12')
        for seminar in d['seminars']:
            self.assertLessEqual(date.fromisoformat(seminar['date_start']),date(2026,10,18))
            for video in seminar['videos']:
                url=urlsplit(video['embed_url'])
                self.assertIn(url.hostname,('vk.com','vkvideo.ru'))
                self.assertEqual(url.path,'/video_ext.php')
                self.assertEqual(url.scheme,'https')
                self.assertNotIn('autoplay=',video['embed_url'])
                qs=parse_qs(url.query)
                self.assertRegex(qs['id'][0],r'^[0-9]{5,16}$')
                self.assertEqual(video['owner_id'],qs['oid'][0])
                self.assertEqual(video['is_museum_vk_channel'],video['owner_id']=='-37126776')
                self.assertIn('original_iframe_src',video)
    def test_editorial_integration_and_no_rehosting(self):
        body=(ROOT/'apps/web/src/components/OfficialMuseumScience.tsx').read_text()
        self.assertIn('<OfficialMuseumSeminars />',body)
        self.assertIn('officialSeminarSlugs',body)
        player=(ROOT/'apps/web/src/components/OfficialMuseumSeminars.tsx').read_text()
        self.assertIn('setPlaying(current=>current===key?null:key)',player)
        self.assertIn('loading="lazy"',player)
        self.assertIn('referrerPolicy="no-referrer"',player)
        self.assertIn('sandbox=',player)
