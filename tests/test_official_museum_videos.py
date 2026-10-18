"""Verify original museum-source video titles, VK embed origins and consent policy."""
from __future__ import annotations
import json,unittest,re
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
PIN={
 'museum':('https://muzei-xleb.ru/video/o-muzee',5,'39e08bf45a50c359f61691e608c53607e74b6dc448ff011a1bec74021627d5e0'),
 'exhibitions':('https://muzei-xleb.ru/video/vystavky',21,'6412db5f523932cab22c1688b1abc65b5015c6a056168063972ff026854d40fa'),
 'unusual-tour':('https://muzei-xleb.ru/video/proekt-neobzornaya-ekskursiya',6,'f78fa4a698874caa4a58a7ce82f8105646f0d7b88416713f363b18f9afbaccab'),
}
class OriginalMuseumVideosTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.d=json.loads((ROOT/'apps/web/src/data/official-museum-videos.json').read_text())
    def test_exact_original_museum_pages_and_counts(self):
        d=self.d
        self.assertEqual(d['source'],'https://muzei-xleb.ru')
        self.assertEqual(d['source_index_url'],'https://muzei-xleb.ru/video')
        self.assertEqual((d['group_count'],d['video_count'],d['vk_embeds'],d['external_mp4_file_links']),(3,32,31,1))
        self.assertEqual(set(x['slug'] for x in d['groups']),set(PIN))
        self.assertEqual(len({x['id'] for g in d['groups'] for x in g['videos']}),32)
        for group in d['groups']:
            with self.subTest(group=group['slug']):
                url,amount,digest=PIN[group['slug']]
                self.assertEqual((group['source_url'],group['count'],group['source_html_sha256']),(url,amount,digest))
                self.assertEqual(len(group['videos']),amount)
    def test_exact_provider_and_no_autoplay_or_fake_files(self):
        entries=[x for group in self.d['groups'] for x in group['videos']]
        self.assertEqual(Counter(x['kind'] for x in entries),{'vk':31,'external-mp4-link':1})
        self.assertEqual(sum(x.get('hosted_in_museum_vk_group',False) for x in entries),26)
        for x in entries:
            with self.subTest(video=x['id']):
                self.assertTrue(x['third_party_embed_requires_click'])
                self.assertTrue(x['title'] and len(x['title'])>=6)
                self.assertTrue(x['source_page'].startswith('https://muzei-xleb.ru/video/'))
                self.assertTrue(x['source_iframe_src'].startswith('https://'))
                if x['kind']=='vk':
                    self.assertNotIn('autoplay=',x['embed_url'])
                    parsed=urlsplit(x['embed_url'])
                    self.assertEqual(parsed.scheme,'https')
                    self.assertIn(parsed.hostname,{'vk.com','vkvideo.ru'})
                    self.assertEqual(parsed.path,'/video_ext.php')
                    q=parse_qs(parsed.query)
                    self.assertRegex(q['id'][0],r'^[0-9]{5,16}$')
                    self.assertEqual(q['oid'][0],x['video_owner_id'])
                    self.assertEqual(x['hosted_in_museum_vk_group'],q['oid'][0]=='-37126776')
                    self.assertNotIn('direct_file_url',x)
                else:
                    self.assertIsNone(x['embed_url'])
                    self.assertTrue(x['direct_file_url'].startswith('https://cdnvideo.tvspb.ru/tvspbru-uploads/2026/09/'))
                    self.assertTrue(x['direct_file_url'].endswith('.mp4'))
    def test_strict_third_party_scope(self):
        csp=(ROOT/'scripts/build_csp.py').read_text()
        self.assertIn('frame-src https://yandex.ru https://vk.com https://vkvideo.ru',csp)
        self.assertIn("\"connect-src 'self'\"",csp)
        self.assertIn("\"img-src 'self' data:\"",csp)
        self.assertNotIn('script-src https://vk.com',csp)
        self.assertNotIn('script-src https://vkvideo.ru',csp)
        component=(ROOT/'apps/web/src/components/OfficialMuseumVideoLibrary.tsx').read_text()
        self.assertIn('playing===video.id',component)
        self.assertIn('setPlaying(null)',component)
        self.assertIn('referrerPolicy=\"no-referrer\"',component)
        self.assertIn('sandbox=',component)
