"""Never assume a source XML sitemap exists or ignore old crawler policy."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class OfficialMuseumRobotsAndSitemapBaselineTests(unittest.TestCase):
 def test_both_old_live_hosts_use_identical_robot_rules_and_no_standard_sitemap(self):
  root=ROOT/'.local_archive/seo-old-site-indexation'
  d=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
  self.assertEqual(len(d['files']),4)
  expected={
   '/robots.txt':(200,'robots.txt'),
   '/sitemap.xml':(404,'sitemap.xml'),
   'https://www.muzei-xleb.ru/robots.txt':(200,'www-robots.txt'),
   'https://www.muzei-xleb.ru/sitemap.xml':(404,'www-sitemap.xml'),
  }
  self.assertEqual(set(expected),{r['path'] for r in d['files']})
  for r in d['files']:
   with self.subTest(path=r['path']):
    expected_status,name=expected[r['path']]
    self.assertEqual(r['http_status'],expected_status)
    raw=(root/name).read_bytes()
    self.assertEqual(hashlib.sha256(raw).hexdigest(),r['sha256'])
    self.assertEqual(len(raw),r['bytes'])
  bare=(root/'robots.txt').read_bytes()
  self.assertEqual(bare,(root/'www-robots.txt').read_bytes())
  self.assertIn(b'Crawl-delay: 10',bare)
  self.assertIn(b'Disallow: /admin/',bare)
  self.assertIn(b'Disallow: /search/',bare)
  self.assertFalse(any(l.lower().startswith('sitemap:') for l in bare.decode().splitlines()))

 def test_preview_robots_remain_completely_disallowed_and_sitemap_empty(self):
  out=ROOT/'apps/web/out'
  self.assertEqual((out/'robots.txt').read_text().strip(),'User-Agent: *\nDisallow: /')
  self.assertNotIn('<url>',(out/'sitemap.xml').read_text())
  src=(ROOT/'apps/web/src/data/seo-routes.ts').read_text()
  self.assertIn('crawlDelay:approved?10:undefined',src)
  self.assertIn('"/admin/"',src)
  self.assertIn('"/cms/"',src)
  self.assertIn('"/search/"',src)

if __name__=='__main__':unittest.main()
