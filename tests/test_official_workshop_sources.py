"""Public workshop catalogue is exactly the source edition, not invented offerings."""
import hashlib,json,re,unittest
from pathlib import Path
from lxml import html

ROOT=Path(__file__).resolve().parents[1]
class WorkshopProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'apps/web/src/data/official-workshop-pages.json').read_text())

    def test_twelve_workshops_reproduce_real_museum_catalogue_without_duplicates(self):
        d=self.data
        self.assertEqual(d['source'],'https://muzei-xleb.ru')
        self.assertEqual(d['count'],12)
        index=d['index']
        self.assertEqual(index['source_url'],'https://muzei-xleb.ru/master-klassy')
        self.assertEqual(hashlib.sha256(index['html'].encode()).hexdigest(),index['html_sha256'])
        old=html.fromstring('<div>'+index['html']+'</div>')
        museum_urls={a.get('href') for a in old.xpath('.//a[@href]')
                     if '/master-klassy/' in a.get('href') or '/ekskursii/master-klass-' in a.get('href')}
        self.assertEqual({p['source_url'] for p in d['programs']},museum_urls)
        self.assertEqual(len(museum_urls),12)
        self.assertEqual(len({p['slug'] for p in d['programs']}),12)

    def test_every_workshop_is_source_attested_and_photo_rights_are_unconfirmed(self):
        ages=[]
        for p in self.data['programs']:
            with self.subTest(slug=p['slug']):
                self.assertEqual(p['source_url'],'https://muzei-xleb.ru'+p['path'])
                self.assertEqual(p['slug'],'museum-workshop-'+p['path'].rsplit('/',1)[-1])
                self.assertEqual(hashlib.sha256(p['html'].encode()).hexdigest(),p['html_sha256'])
                self.assertEqual(p['intro'],' '.join(html.fromstring('<div>'+p['html']+'</div>').text_content().split())[:245])
                self.assertIs(p['photos_rights_confirmed'],False)
                self.assertNotIn('<img',p['html'].lower())
                self.assertNotIn('<script',p['html'].lower())
                txt=html.fromstring('<div>'+p['html']+'</div>').text_content()
                match=re.search(r'Возраст:\s*(\d+)\+',txt)
                self.assertIsNotNone(match,'Original museum age threshold must be visible')
                ages.append(int(match.group(1)))
        self.assertEqual(min(ages),6)
        self.assertEqual(max(ages),10)

    def test_shop_has_no_fake_merchandise_seed_or_sales_ui(self):
        component=(ROOT/'apps/web/src/components/MuseumShopShowcase.tsx').read_text()
        self.assertIn('items.length>0',component)
        self.assertIn('нет корзины',component)
        self.assertIn('не обнаружен подтверждённый каталог',component)
        self.assertNotIn('<form',component)
        self.assertNotIn('checkout',component.replace('checkout, customer',''))
