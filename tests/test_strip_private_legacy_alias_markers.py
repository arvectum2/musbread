"""Transient noindex alias markers must never ship in a Next static build."""
import csv
import tempfile
import unittest
from pathlib import Path
from scripts.build_museum_legacy_page_aliases import render_alias
from scripts.strip_private_legacy_alias_markers import strip

class MarkerStripTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"out";self.root.mkdir()
        (self.root/"index.html").write_text("<h1>Home</h1>")
        self.source="/node/123";self.target="/guide/museum/"
        self.alias=self.root/"node/123/index.html";self.alias.parent.mkdir(parents=True)
        self.alias.write_text(render_alias(self.source,self.target))
        self.marker=self.alias.parent/".musbread-legacy-alias";self.marker.write_text(self.target+"\n")
        self.csv=Path(self.temp.name)/"manifest.csv"
        with self.csv.open("w",encoding="utf-8-sig",newline="") as h:
            w=csv.DictWriter(h,fieldnames=["legacy_path","new_relative_url","source_kind","mode"],delimiter=";");w.writeheader()
            w.writerow({"legacy_path":self.source,"new_relative_url":self.target,"source_kind":"source-verified-drupal-node","mode":"static-meta-refresh; HTTP 301 requires approved webserver config"})

    def test_removes_only_verified_ephemeral_marker(self):
        self.assertEqual(strip(self.root,self.csv),1)
        self.assertFalse(self.marker.exists())
        self.assertEqual(self.alias.read_text(),render_alias(self.source,self.target))
        with self.assertRaisesRegex(ValueError,"missing legacy marker"):
            strip(self.root,self.csv)

    def test_tampering_does_not_partially_remove_markers(self):
        self.alias.write_text(self.alias.read_text().replace("noindex,follow","index,follow"))
        with self.assertRaisesRegex(ValueError,"bytes or route manifest changed"):
            strip(self.root,self.csv)
        self.assertTrue(self.marker.exists())

    def test_unknown_extra_marker_blocks_clean(self):
        extra=self.root/"private/.musbread-legacy-alias";extra.parent.mkdir()
        extra.write_text("/unsafe/\n")
        with self.assertRaisesRegex(ValueError,"Unexpected or missing legacy marker"):
            strip(self.root,self.csv)
        self.assertTrue(self.marker.exists())

if __name__=='__main__':unittest.main()
