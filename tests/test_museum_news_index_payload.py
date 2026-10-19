"""Archived full news bodies remain on 280 source-preserving detail pages.

The index must not inline 270 long HTML bodies: it makes the site slow on
mobile and unnecessarily sends duplicate text to every news-index visitor.
"""
import json
import unittest
from pathlib import Path
from lxml import html

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"apps/web/out"
DATA=ROOT/"apps/web/src/data"

class MuseumNewsIndexPayloadTests(unittest.TestCase):
    def test_archived_index_is_navigation_not_duplicate_full_article_library(self):
        index=OUT/"news/index.html"
        self.assertTrue(index.is_file())
        self.assertLess(index.stat().st_size,1_150_000,
                        "Archive index embeds too much duplicated content")
        doc=html.fromstring(index.read_bytes())
        region=doc.xpath('//section[contains(concat(" ",normalize-space(@class)," ")," museum-news-archive ")]')
        self.assertEqual(len(region),1)
        cards=region[0].xpath('.//article[contains(concat(" ",normalize-space(@class)," ")," official-museum-program-card ")]')
        self.assertEqual(len(cards),270)
        self.assertFalse(region[0].xpath('.//details//div[contains(@class,"rich-text")]'),
                         "All full texts belong to the source-verified article pages")
        self.assertEqual(len(region[0].xpath('.//a[contains(text(),"Читать полный текст архивной новости")]')),
                         sum(bool(x.get("html")) for x in json.loads((DATA/"official-museum-news-archive.json").read_text())["articles"]))

    def test_every_source_archived_news_has_unchanged_full_original_page(self):
        articles=json.loads((DATA/"official-museum-news-archive.json").read_text())["articles"]
        self.assertEqual(len(articles),270)
        for item in articles:
            old="/"+item["source_url"].split("/",3)[-1].strip("/")+"/"
            page=OUT/old.lstrip("/")/"index.html"
            with self.subTest(path=old):
                self.assertTrue(page.is_file(),old)
                doc=html.fromstring(page.read_bytes())
                self.assertEqual(doc.xpath('//link[@rel="canonical"]/@href'),[item["source_url"]])

if __name__=="__main__": unittest.main()
