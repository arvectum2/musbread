from __future__ import annotations
import hashlib, json, re, unittest
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"apps/web/src/data/official-page-snapshots.json"
class OfficialSourceSnapshotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(DATA.read_text())
    def test_only_verified_museum_pages_and_safe_markup(self):
        data=self.data
        self.assertEqual(data["source"],"https://muzei-xleb.ru")
        self.assertEqual(data["count"],len(data["pages"]))
        self.assertGreaterEqual(data["count"],16)
        paths=[r["path"] for r in data["pages"]]
        self.assertEqual(len(paths),len(set(paths)))
        for page in data["pages"]:
            self.assertEqual(page["source_url"],data["source"]+page["path"])
            self.assertTrue(page["title"])
            self.assertGreater(page["text_length"],30)
            self.assertEqual(hashlib.sha256(page["html"].encode()).hexdigest(),page["html_sha256"])
            self.assertNotRegex(page["html"].lower(),r"<(?:script|iframe|form|object|img)\b")
            self.assertNotRegex(page["html"].lower(),r"javascript:|onerror=|onclick=")
            for doc in page["document_links"]:
                self.assertEqual(urlparse(doc["url"]).hostname,"muzei-xleb.ru")
    def test_current_admin_privacy_and_visiting_are_backed_by_source(self):
        pages={r["path"]:r for r in self.data["pages"]}
        admin=pages["/administraciya"]["html"]
        self.assertNotIn("Катерина Алексеевна Запускалова",admin)
        self.assertIn("Елизавета Вилорьевна Тапакова-Боярская",admin)
        self.assertEqual(len(pages["/politika-konfidencialnosti-i-obrabotki-personalnyh-dannyh"]["document_links"]),2)
        self.assertIn("400 рублей",pages["/stoimost"]["html"])
        self.assertIn("01.09.2026",pages["/stoimost"]["html"])
        self.assertIn("1988",pages["/o-muzee"]["html"])
    def test_catalogs_are_reported_as_nonarticle_indexes(self):
        self.assertEqual({x["path"] for x in self.data["errors"]},{"/posetitelyam"})
        self.assertIn("/ekspozicii/2024-",next(x for x in self.data["pages"] if x["path"]=="/ekspozicii")["html"])
if __name__=="__main__":unittest.main()
