import hashlib
import json
import unittest
from pathlib import Path
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
HOST = "https://muzei-xleb.ru"

class OfficialExpositionRoomsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT/"apps/web/src/data/official-exposition-rooms.json").read_text())
        source = json.loads((ROOT/"apps/web/src/data/official-page-snapshots.json").read_text())
        cls.listing = next(x for x in source["pages"] if x["path"] == "/ekspozicii")

    def test_all_eleven_rooms_match_existing_museum_index(self):
        self.assertEqual(self.data["source"], HOST)
        anchors = html.fromstring("<div>"+self.listing["html"]+"</div>").xpath(".//a[@href]")
        self.assertEqual(len(anchors), 11)
        self.assertEqual(
            [(x.get("href"), x.text_content().strip()) for x in anchors],
            [(r["source_url"], r["title"]) for r in self.data["rooms"]])
        self.assertEqual(len({r["slug"] for r in self.data["rooms"]}), 11)

    def test_verified_real_room_descriptions(self):
        for room in self.data["rooms"]:
            with self.subTest(room=room["slug"]):
                self.assertTrue(room["source_url"].endswith("/"+room["slug"]))
                self.assertTrue(room["source_url"].startswith(HOST+"/ekspozicii/"))
                self.assertEqual(hashlib.sha256(room["html"].encode()).hexdigest(),
                                 room["html_sha256"])
                self.assertGreater(room["description_length"], 250)
                self.assertGreater(len(room["excerpt"]), 40)
                self.assertNotIn("<script", room["html"].lower())
                self.assertNotIn("<img", room["html"].lower())

    def test_museum_photos_are_provenance_only_pending_rights(self):
        self.assertGreaterEqual(sum(len(r["image_sources"]) for r in self.data["rooms"]), 50)
        for room in self.data["rooms"]:
            self.assertIs(room["media_rights_confirmed"], False)
            for image in room["image_sources"]:
                self.assertTrue(image["source_url"].startswith(
                    HOST + "/sites/default/files/"))
