"""A verified original legal page must survive even when no duplicate guide route exists."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import build_museum_legacy_page_aliases as a

class NativeMuseumSourceAliasTests(unittest.TestCase):
    def test_existing_source_backed_page_does_not_require_nonexistent_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            orig=root/"my-ispolzuem-cookie/index.html"
            orig.parent.mkdir(parents=True)
            orig.write_text(
                '<html><head><link rel="canonical" href="https://muzei-xleb.ru/my-ispolzuem-cookie">'
                '</head><body><main data-original-museum-section="my-ispolzuem-cookie">'
                'Source-backed historical legal text</main></body></html>',encoding="utf-8")
            mapping={"/my-ispolzuem-cookie":{"target":"/guide/museum-cookie/",
                                           "why":"original-source-section"}}
            with patch.object(a,"OUT",root),patch.object(a,"build_map",return_value=mapping):
                result=a.build_aliases(write=False,strict=True)
            self.assertEqual(result["missing"],[])
            self.assertEqual(result["collisions"],[])
            self.assertEqual(result["rows"][0]["new_relative_url"],"/my-ispolzuem-cookie")
            self.assertEqual(result["rows"][0]["mode"],"native-source-URL-200; no redirect")

    def test_missing_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(a,"OUT",Path(tmp)),patch.object(a,"build_map",
                return_value={"/my-ispolzuem-cookie":{"target":"/guide/museum-cookie/",
                             "why":"original-source-section"}}):
                with self.assertRaisesRegex(RuntimeError,"Unknown/missing destination"):
                    a.build_aliases(write=False,strict=True)

if __name__=="__main__":
    unittest.main()
