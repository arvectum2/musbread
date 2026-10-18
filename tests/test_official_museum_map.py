"""The actual official Yandex map constructor and social IDs: provenance and privacy."""
import hashlib,json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class OfficialMuseumMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info=json.loads((ROOT/'apps/web/src/data/official-museum-map.json').read_text())
    def test_map_from_real_museum_contacts_not_guessed_geocoordinates(self):
        i=self.info
        self.assertEqual(i['museum_contact_source'],'https://muzei-xleb.ru/kontakty')
        self.assertEqual(i['map_provider'],'Яндекс Карты')
        self.assertEqual(i['constructor_id'],'He-zSYLQhEw4RVkaykZ0Rpr1lOWx3f9O')
        self.assertEqual(i['widget_iframe_url'],
            'https://yandex.ru/map-widget/v1/?um=constructor%3AHe-zSYLQhEw4RVkaykZ0Rpr1lOWx3f9O&source=constructor')
        self.assertIn('sid='+i['constructor_id'],i['official_original_script_url'])
        self.assertEqual(hashlib.sha256(i['official_original_script_url'].encode()).hexdigest(),
                         i['original_script_url_sha256'])
        self.assertTrue(i['embedded_after_user_action_only'])
        self.assertTrue(i['no_inferred_coordinates'])
        self.assertRegex(i['http_200_verified_utc'],r'^2026-10-18T')
    def test_web_security_csp_does_not_allow_yandex_scripts_or_extra_trackers(self):
        s=(ROOT/'scripts/build_csp.py').read_text()
        self.assertIn('"frame-src https://yandex.ru"',s)
        self.assertNotIn('"script-src https://yandex.ru"',s)
        self.assertNotIn('"connect-src https://yandex.ru"',s)
        self.assertIn('frame-ancestors',s)
    def test_source_social_ids_still_in_museum_metadata(self):
        m=(ROOT/'apps/web/src/data/museum-reference.ts').read_text()
        self.assertIn('https://vk.com/club37126776',m)
        self.assertIn('https://max.ru/id7808018523_gos',m)
        self.assertIn('https://muzei-xleb.ru/kontakty',
                      (ROOT/'apps/web/src/components/OfficialMuseumSocialLinks.tsx').read_text())
