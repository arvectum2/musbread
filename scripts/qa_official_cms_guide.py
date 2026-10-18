#!/usr/bin/env python3
"""Isolated CMS draft->approved-export->static guide integration smoke check.

Uses a disposable copy of the Mac mini local CMS database, NEVER the source DB.
The temporary Next build is independent of the tracked fixture or working out/.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
CMS = ROOT / "apps/cms"
WEB = ROOT / "apps/web"
PRIVATE = ROOT / ".local_archive"
REQUIRED = {"museum-privacy", "tickets-and-benefits", "ticket-refunds", "museum-history",  "museum-documents", "museum-finance", "museum-anti-corruption", "accessible-museum", "pushkin-card", "faq", "zal-hleb-v-mirovoy-istorii", "excursion-overview", "excursion-interactive", "excursion-thematic",
            "excursion-theatrical", "children-interactive", "children-thematic", "museum-tour-kolobok",
            "museum-tour-interaktivnaya-programma-dlya-detey-lovi-ritm",
            "museum-shop", "children-workshops", "excursion-workshops-adults",
            "museum-workshop-kukly-kuvadki"}


def run(command: list[str], cwd: Path, env: dict, log: Path) -> None:
    with log.open("a", encoding="utf-8") as stream:
        subprocess.run(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)


def main() -> None:
    if (CMS / "bootstrap/cache/config.php").exists():
        raise RuntimeError("Laravel config cache present: isolated DB cannot be guaranteed")
    source_db = CMS / "database/database.sqlite"
    with sqlite3.connect(f"file:{source_db}?mode=ro", uri=True) as db:
        originals = dict(db.execute(
            "select slug,status from museum_entries where slug in ("
            + ",".join("?" * len(REQUIRED)) + ")", sorted(REQUIRED)))
        if set(originals) != REQUIRED or any(x != "draft" for x in originals.values()):
            raise RuntimeError("Cannot run: source CMS editions are not all private drafts")
        expected_docs = {
            slug: list(db.execute(
                "select d.sha256,d.file_type,d.size_bytes,d.storage_path "
                "from museum_documents d join museum_entries e on d.museum_entry_id=e.id "
                "where e.slug=? order by d.id", (slug,)
            ))
            for slug in ("museum-privacy", "ticket-refunds", "museum-documents",
                         "tickets-and-benefits", "museum-finance", "museum-anti-corruption")
        }
        expected_counts = {"museum-privacy": 2, "ticket-refunds": 2,
                            "museum-documents": 19, "tickets-and-benefits": 1,
                           "museum-finance": 4, "museum-anti-corruption": 15}
        if any(len(expected_docs[slug]) != count for slug,count in expected_counts.items()):
            raise RuntimeError("Missing imported official documents or compressed copies in CMS")
        with sqlite3.connect(f"file:{source_db}?mode=ro", uri=True) as db:
            n = db.execute("select count(*) from museum_entries where status='draft'"
                           " and slug like 'zal-%'").fetchone()[0]
            if n != 11:
                raise RuntimeError("Eleven imported official exposition rooms must all be draft")
            n = db.execute("select count(*) from museum_entries "
                           "where slug like 'museum-tour-%' and type='excursion' and status='draft'").fetchone()[0]
            if n != 17:
                raise RuntimeError("All 17 source-backed museum excursions must be unpublished working drafts")
            n = db.execute("select count(*) from museum_entries "
                           "where slug like 'museum-workshop-%' and status='draft'").fetchone()[0]
            if n != 12:
                raise RuntimeError("All 12 real museum workshop source pages must remain drafts")
            n = db.execute("select count(*) from museum_entries where status='draft'").fetchone()[0]
            if n != 63:
                raise RuntimeError("Private working CMS count changed: expected 63 drafts")

    with tempfile.TemporaryDirectory(prefix="museum-guide-qa-", dir=PRIVATE) as name:
        work = Path(name)
        db_path = work / "museum-copy.sqlite"
        # SQLite backup API also provides a consistent copy if local DB is in WAL mode.
        with sqlite3.connect(f"file:{source_db}?mode=ro", uri=True) as source, sqlite3.connect(db_path) as target:
            source.backup(target)
        with sqlite3.connect(db_path) as db:
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes'),"
                       "h1='QA: заголовок из редактируемой CMS',"
                       "seo_title='QA: заголовок SEO из CMS',"
                       "seo_description='QA: описание поискового сниппета'"
                       "where slug='museum-privacy'")
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes') "
                       "where slug in ('tickets-and-benefits','ticket-refunds','museum-documents','museum-finance','museum-anti-corruption','accessible-museum','pushkin-card','faq')")
            db.execute("update museum_sections set status='published' "
                       "where slug in ('children-interactive','children-thematic')")
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes') "
                       "where slug in ('children-interactive','children-thematic')")
            db.execute("update museum_sections set status='published' "
                       "where slug in ('museum-shop','children-workshops','excursion-workshops-adults')")
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes') "
                       "where slug in ('museum-shop','children-workshops','excursion-workshops-adults')")
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes'),"
                       "title='QA: обновлённый редактором мастер-класс Кувадка',"
                       "excerpt='QA: редакторская аннотация программы Кувадка.',"
                       "body='<p>QA: отредактированное содержание мастер-класса Кувадка.</p>' "
                       "where slug='museum-workshop-kukly-kuvadki'")
            shop_section_id = db.execute(
                "select id from museum_sections where slug='museum-shop'").fetchone()[0]
            db.execute("insert into museum_entries "
                       "(type,slug,title,body,status,published_at,museum_section_id,excerpt) "
                       "values ('page','qa-shop-catalog-item','QA ONLY: проверочный сувенир',"
                       "'<p>Временная проверка редакторского элемента витрины, не реальный товар.</p>',"
                       "'published',datetime('now','-10 minutes'),?,"
                       "'QA ONLY: несуществующая тестовая позиция.')",(shop_section_id,))
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes') "
                       "where slug in ('excursion-overview','excursion-interactive',"
                       "'excursion-thematic','excursion-theatrical')")
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes'),"
                       "title='QA: музей отредактировал программу Колобок',"
                       "excerpt='QA: аннотация после редактора.',"
                       "body='<p>QA: изменённое описание программы Колобок.</p>' "
                       "where slug='museum-tour-kolobok'")
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes'),"
                       "title='QA: новая интерактивная программа',"
                       "excerpt='QA: новый анонс интерактивной программы.',"
                       "body='<p>QA: новая интерактивная программа от редактора.</p>' "
                       "where slug='museum-tour-interaktivnaya-programma-dlya-detey-lovi-ritm'")
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes'),"
                       "title='QA: редакция зала утверждена музеем',"
                       "excerpt='QA: краткая новая аннотация к залу.',"
                       "body='<p>QA: новое редакционное описание мирового хлеба.</p>' "
                       "where slug='zal-hleb-v-mirovoy-istorii'")
            db.commit()

        environment = dict(os.environ)
        environment.update({
            "APP_ENV": "testing",
            "DB_CONNECTION": "sqlite",
            "DB_DATABASE": str(db_path),
            "DB_URL": "",
            "CACHE_STORE": "array",
            "QUEUE_CONNECTION": "sync",
            "MUSEUM_ENABLE_APPROVAL_QUEUE": "false",
            "MUSEUM_USE_PUBLISH_QUEUE": "false",
            "MUSBREAD_SITE_APPROVED": "",
            "NEXT_TELEMETRY_DISABLED": "1",
        })
        snapshot = work / "published.json"
        manifest = work / "manifest.json"
        assets = work / "assets"
        documents = assets / "documents"
        media = assets / "media"
        log = work / "qa.log"
        run(["php", "artisan", "museum:export",
             "--output=" + str(snapshot), "--manifest=" + str(manifest),
             "--document-output-dir=" + str(documents),
             "--media-output-dir=" + str(media),
             "--preflight-strict"], CMS, environment, log)
        data = json.loads(snapshot.read_text())
        slugs = {entry["slug"] for entry in data["entries"]}
        if not {"museum-privacy", "tickets-and-benefits", "ticket-refunds", "museum-documents",
                "museum-finance", "museum-anti-corruption", "accessible-museum", "pushkin-card", "faq"} <= slugs or "museum-history" in slugs:
            raise RuntimeError("Public/private source CMS entries wrongly filtered: " + repr(slugs))
        published_room = next((e for e in data["entries"]
                               if e["slug"] == "zal-hleb-v-mirovoy-istorii"), None)
        if not published_room or published_room["title"] != "QA: редакция зала утверждена музеем":
            raise RuntimeError("Edited museum exposition room was not exported")
        if any(e["slug"].startswith("zal-") and
               e["slug"] != "zal-hleb-v-mirovoy-istorii" for e in data["entries"]):
            raise RuntimeError("Private museum exposition room draft was exported")
        published_tours = {e["slug"] for e in data["entries"] if e["slug"].startswith("museum-tour-")}
        expected_tours = {"museum-tour-kolobok",
            "museum-tour-interaktivnaya-programma-dlya-detey-lovi-ritm"}
        if published_tours != expected_tours:
            raise RuntimeError("Only two edited excursion programs may pass isolated publication gate: "
                + repr(published_tours))
        for slug in ("excursion-overview","excursion-interactive",
                     "excursion-thematic","excursion-theatrical"):
            if slug not in slugs:
                raise RuntimeError("CMS category page missing from isolated publication: "+slug)
        if not {"children-interactive","children-thematic"} <= slugs:
            raise RuntimeError("Two children information pages missing in test-published CMS export")
        attachment_hrefs = {}
        for slug, recorded in expected_docs.items():
            item = next(entry for entry in data["entries"] if entry["slug"] == slug)
            if len(item.get("documents", [])) != expected_counts[slug]:
                raise RuntimeError("Wrong count of source-backed CMS attachments in " + slug)
            hashes = {sha for sha, _ext, _bytes, _storage in recorded}
            attachment_hrefs[slug] = set()
            for attachment in item["documents"]:
                href = attachment["href"]
                if attachment["accessibility_reviewed"] or not href.startswith("/documents/"):
                    raise RuntimeError("Originals must remain flagged unreviewed and use /documents/")
                actual = documents / Path(href).name
                digest = hashlib.sha256(actual.read_bytes()).hexdigest()
                if digest not in hashes or int(attachment["size_bytes"]) != actual.stat().st_size:
                    raise RuntimeError("Exported local document differs from private CMS SHA256/size")
                attachment_hrefs[slug].add(href)
            if len(attachment_hrefs[slug]) != expected_counts[slug]:
                raise RuntimeError("Document duplicate URI in " + slug)
        compressed = next(d for d in expected_docs["museum-privacy"] if d[2] > 10_000_000)
        if compressed[2] != 14_548_332:
            raise RuntimeError("Verified compressed 42-page privacy PDF missing from isolation")
        if not any("/documents/"+compressed[0]+".pdf" == h for h in attachment_hrefs["museum-privacy"]):
            raise RuntimeError("Compressed PDF URL absent from public export")

        labor = next(d for d in expected_docs["museum-documents"] if d[2] == 13_815_877)
        if "/documents/"+labor[0]+".pdf" not in attachment_hrefs["museum-documents"]:
            raise RuntimeError("Verified compressed 45-page work rules PDF not in CMS export")

        expected_safe = {
            "museum-finance": {
                "49d9a017dd17d60cda02105d7b28c5faf09e1dbb0f423f1e8efccf98aab73d3b",
                "3758e315468d441eb1f1868f625e04c8e178b7220edd0ebaeaea56462357a7bb",
            },
            "museum-anti-corruption": {
                "d60ddc0f9e105303ce0a358462ba7cbd0e078982dff8a645fdf14753fda8bfcb",
            },
        }
        for slug, checksums in expected_safe.items():
            recorded = {entry[0] for entry in expected_docs[slug]}
            if not checksums <= recorded:
                raise RuntimeError("One or more of three safety-validated derived PDFs missing in " + slug)
            for sha in checksums:
                if "/documents/" + sha + ".pdf" not in attachment_hrefs[slug]:
                    raise RuntimeError("Reconstructed museum file not served by PHP exporter")

        isolated = work / "web"
        shutil.copytree(WEB, isolated, ignore=shutil.ignore_patterns(
            "node_modules", ".next", "out", "test-results", "playwright-report", ".git"))
        (isolated / "node_modules").symlink_to(WEB / "node_modules", target_is_directory=True)
        shutil.copyfile(snapshot, isolated / "src/data/published.json")
        shutil.copyfile(manifest, isolated / "public/snapshot-manifest.json")
        shutil.copytree(documents, isolated / "public/documents", dirs_exist_ok=True)
        run(["npm", "run", "build", "--", "--webpack"], isolated, environment, log)

        out = isolated / "out"
        privacy = html.fromstring((out / "guide/museum-privacy/index.html").read_bytes())
        prices = html.fromstring((out / "guide/tickets-and-benefits/index.html").read_bytes())
        refunds = html.fromstring((out / "guide/ticket-refunds/index.html").read_bytes())
        hub = html.fromstring((out / "guide/museum-documents/index.html").read_bytes())
        finance = html.fromstring((out / "guide/museum-finance/index.html").read_bytes())
        anticorruption = html.fromstring((out / "guide/museum-anti-corruption/index.html").read_bytes())
        access = html.fromstring((out / "guide/accessible-museum/index.html").read_bytes())
        pushkin = html.fromstring((out / "guide/pushkin-card/index.html").read_bytes())
        if "Содержание, опубликованное редактором музея" not in access.text_content():
            raise RuntimeError("Current accessible-museum source not editable through approved CMS release")
        if "Вход и вестибюль оборудованы пандусами" not in access.text_content():
            raise RuntimeError("Museum accessible visitor source lost in CMS publication")
        if "Содержание, опубликованное редактором музея" not in pushkin.text_content():
            raise RuntimeError("Pushkin card source is not editable through approved CMS release")
        if "14 до 22 лет" not in pushkin.text_content():
            raise RuntimeError("Pushkin card museum source body lost")
        if "https://vmuzey.com/museum/sankt-peterburgskiy-muzey-hleba" not in pushkin.xpath("//main//a/@href"):
            raise RuntimeError("Museum ticket partner source URL lost in Pushkin card")
        faq = html.fromstring((out / "guide/faq/index.html").read_bytes())
        if "Содержание, опубликованное редактором музея" not in faq.text_content():
            raise RuntimeError("FAQ publication did not use editable MoonShine source")
        if len(faq.xpath("//main//section[contains(@class,'official-source-content')]//h2")) != 10:
            raise RuntimeError("Nine editorial FAQ questions were not shown from CMS")
        if faq.xpath("//main//section[contains(@class,'visitor-faq')]"):
            raise RuntimeError("Stale public FAQ fallback duplicated published CMS answers")
        if "Официальный музейный первоисточник" not in faq.text_content():
            raise RuntimeError("FAQ official source provenance lost in true CMS export")
        fallback = html.fromstring((out / "guide/museum-history/index.html").read_bytes())
        exhibit = html.fromstring((out / "guide/museum-exposition/index.html").read_bytes())
        edited_room = html.fromstring(
            (out / "museum/zal-hleb-v-mirovoy-istorii/index.html").read_bytes())
        if len(exhibit.xpath("//main//article[contains(@class,'exposition-card')]")) != 11:
            raise RuntimeError("New exposition source-backed catalogue lost a room")
        if "QA: редакция зала утверждена музеем" not in exhibit.text_content():
            raise RuntimeError("Published CMS room did not replace its source-backed title")
        if "QA: новое редакционное описание мирового хлеба" not in exhibit.text_content():
            raise RuntimeError("Published CMS room did not replace its original body")
        if "История цивилизаций – это история хлеба" in exhibit.text_content():
            raise RuntimeError("Stale official content overlaid an approved changed CMS room")
        if "QA: редакция зала утверждена музеем" not in edited_room.text_content():
            raise RuntimeError("Published room detail URL did not build")
        if len(exhibit.xpath("//main//article[contains(@class,'exposition-card')]//a"
                             "[starts-with(@href,'/museum/')]")) != 1:
            raise RuntimeError("Unpublished source rooms got a private CMS link")

        children_interactive = html.fromstring(
            (out / "guide/children-interactive/index.html").read_bytes())
        children_thematic = html.fromstring(
            (out / "guide/children-thematic/index.html").read_bytes())
        for kind, doc, count in (("children-interactive",children_interactive,6),
                                 ("children-thematic",children_thematic,9)):
            if len(doc.xpath("//main//article[contains(@class,'official-museum-program-card')]")) != count:
                raise RuntimeError("CMS children subcategory "+kind+" lost source program cards")
            if "Содержание, опубликованное редактором музея" not in doc.text_content():
                raise RuntimeError("Editorially approved children section CMS body not displayed: "+kind)
        interactive = html.fromstring((out / "guide/excursion-interactive/index.html").read_bytes())
        thematic = html.fromstring((out / "guide/excursion-thematic/index.html").read_bytes())
        theatrical = html.fromstring((out / "guide/excursion-theatrical/index.html").read_bytes())
        overview = html.fromstring((out / "guide/excursion-overview/index.html").read_bytes())
        for kind, doc, count in (("interactive",interactive,6),
                                 ("thematic",thematic,9),("theatrical",theatrical,2)):
            if len(doc.xpath("//main//article[contains(@class,'official-museum-program-card')]")) != count:
                raise RuntimeError("Isolated CMS excursion "+kind+" cards lost official source programs")
        if "QA: новая интерактивная программа от редактора" not in interactive.text_content():
            raise RuntimeError("Published editor version failed to replace program text in actual static HTML")
        if len(interactive.xpath("//main//article[contains(@class,'official-museum-program-card')]"
                                 "//a[starts-with(@href,'/excursions/')]")) != 1:
            raise RuntimeError("One edited interactive tour should link internally; five drafts must stay private")
        if "QA: музей отредактировал программу Колобок" not in theatrical.text_content():
            raise RuntimeError("Theatrical program CMS override missing in actual static HTML")
        if len(theatrical.xpath("//main//article[contains(@class,'official-museum-program-card')]"
                                "//a[starts-with(@href,'/excursions/')]")) != 1:
            raise RuntimeError("Unpublished theatrical program is incorrectly public")
        published_detail=html.fromstring(
            (out/"excursions/museum-tour-kolobok/index.html").read_bytes())
        if "QA: изменённое описание программы Колобок" not in published_detail.text_content():
            raise RuntimeError("New CMS excursion detail public route was not correctly exported")
        if "хлеб для космонавтов" not in overview.text_content():
            raise RuntimeError("Official overview excursion source lost in CMS category page")
        shop = html.fromstring((out/"guide/museum-shop/index.html").read_bytes())
        adults = html.fromstring((out/"guide/excursion-workshops-adults/index.html").read_bytes())
        kids = html.fromstring((out/"guide/children-workshops/index.html").read_bytes())
        for slug, doc in (("children-workshops",kids),
                          ("excursion-workshops-adults",adults)):
            if "Содержание, опубликованное редактором музея" not in doc.text_content():
                raise RuntimeError("Workshop CMS category introduction ignored: "+slug)
            if len(doc.xpath("//main//article[contains(@class,'official-museum-program-card')]")) != 12:
                raise RuntimeError("Published workshop category lost original 12 verified museum programs")
            if "QA: обновлённый редактором мастер-класс Кувадка" not in doc.text_content():
                raise RuntimeError("Museum workshop editor changes did not replace source: "+slug)
        if "Отдельного утверждённого музеем каталога" not in adults.text_content():
            raise RuntimeError("Adult workshop listing claims unverified adult programme")
        if "QA ONLY: проверочный сувенир" not in shop.text_content():
            raise RuntimeError("CMS approved shop item not shown in noncommerce gallery")
        if len(shop.xpath("//main//article[contains(@class,'museum-shop-item')]")) != 1:
            raise RuntimeError("CMS shop cannot list exactly one reviewed editorial item")
        if shop.xpath("//main//section[contains(@class,'museum-shop-showcase')]//form"
                      " | //main//section[contains(@class,'museum-shop-showcase')]//button"):
            raise RuntimeError("Museum storefront must not contain checkout/payment/order forms")
        if not (out/"museum/qa-shop-catalog-item/index.html").is_file():
            raise RuntimeError("CMS reviewed shop item has no working standalone route")
        if not (out/"museum/museum-workshop-kukly-kuvadki/index.html").is_file():
            raise RuntimeError("Approved workshop editor detail URL missing")
        if (out/"museum/museum-workshop-rospis-izrazca/index.html").is_file():
            raise RuntimeError("Unpublished museum workshop draft incorrectly public")
        h1 = [str(x).strip() for x in privacy.xpath("//main//h1/text()")]
        if h1 != ["QA: заголовок из редактируемой CMS"]:
            raise RuntimeError("CMS H1 not authoritative on guide route: " + repr(h1))
        title = privacy.xpath("//head/title/text()")
        desc = privacy.xpath("//head/meta[@name='description']/@content")
        if not any("QA: заголовок SEO из CMS" in x for x in title) or desc != ["QA: описание поискового сниппета"]:
            raise RuntimeError("CMS page title/SEO not authoritative in static Next HTML")
        links = privacy.xpath("//main//a/@href")
        if not attachment_hrefs["museum-privacy"].issubset(set(links)):
            raise RuntimeError("Original and compressed privacy attachments missing from guide")
        for name, hrefs, doc in (
            ("privacy", attachment_hrefs["museum-privacy"], privacy),
            ("refund", attachment_hrefs["ticket-refunds"], refunds),
            ("museum-documents", attachment_hrefs["museum-documents"], hub),
            ("tickets-and-benefits", attachment_hrefs["tickets-and-benefits"], prices),
            ("museum-finance", attachment_hrefs["museum-finance"], finance),
            ("museum-anti-corruption", attachment_hrefs["museum-anti-corruption"], anticorruption),
        ):
            if not hrefs.issubset(set(doc.xpath("//main//section[@aria-label='Документы опубликованной редакции CMS']//a/@href"))):
                raise RuntimeError("CMS attachments missing from dedicated " + name + " document panel")
            for href in hrefs:
                if not (out / href.lstrip("/")).is_file():
                    raise RuntimeError("Static downloadable file missing: " + href)
        if "Правила внутреннего трудового распорядка (сжатая копия)" not in hub.text_content():
            raise RuntimeError("Compressed 45-page scanned original mislabeled or not visible")
        if "Возврат билетов" not in refunds.xpath("//main//h1/text()"):
            raise RuntimeError("CMS-approved refund H1 absent")
        if refunds.xpath("//main//form"):
            raise RuntimeError("Refund page must not upload or collect any passport/bank details")
        if not any("/documents/" + sha + "." + ext in attachment_hrefs["ticket-refunds"]
                   for sha, ext, *_ in expected_docs["ticket-refunds"] if ext == "docx"):
            raise RuntimeError("Museum refund request form DOCX not available for download")
        if "Доступность документа ещё не проверена редактором" not in privacy.text_content():
            raise RuntimeError("Unreviewed PDF incorrectly implies accessible revision")
        if "Редакция из CMS" in fallback.text_content() or "1988" not in fallback.text_content():
            raise RuntimeError("Unpublished CMS history incorrectly replaced official-site reference fallback")
        if "Содержание, опубликованное редактором музея" not in prices.text_content():
            raise RuntimeError("Published CMS price page not shown")
        if not prices.xpath("//main//table") or "400 рублей" not in prices.text_content():
            raise RuntimeError("Original price table lost in complete CMS-to-Next pipeline")
        if "Официальные документы музея" in " ".join(
            x.strip() for x in privacy.xpath("//main//section[@aria-label='Официальные документы музея']//h2/text()")):
            raise RuntimeError("Stale reference-document widget overrides CMS edition")
        if privacy.xpath("//main//section[@aria-label='Материалы раздела: Политика конфиденциальности и обработки персональных данных']//a[contains(@href,'/museum/museum-privacy/')]"):
            raise RuntimeError("Canonical guide CMS page links to itself as unrelated material")
        if "noindex" not in (out / "guide/museum-privacy/index.html").read_text():
            raise RuntimeError("Unapproved prototype source page unexpectedly indexable")
    # Successful exit of context proves disposable DB/assets/build deleted.
    with sqlite3.connect(f"file:{source_db}?mode=ro", uri=True) as db:
        after = dict(db.execute("select slug,status from museum_entries where slug in ("
                                + ",".join("?" * len(REQUIRED)) + ")", sorted(REQUIRED)))
        if after != originals:
            raise RuntimeError("Original CMS draft state was modified")
    print("PASS: 23 isolated published CMS records including 12 real workshop cards"
          " in both adult/children sections, edited workshop detail and a QA-only"
          " synthetic shop item (on disposable DB ONLY), zero checkout/forms,"
          " 4 original excursion categories, 17 excursion listings,"
          " 11 halls, nine FAQ and 44 unchanged museum files with SHA256;"
          " working CMS remains 63 private drafts/44 docs, no demo item copied back.")


if __name__ == "__main__":
    main()
