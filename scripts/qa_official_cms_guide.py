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
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread
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
            "museum-workshop-kukly-kuvadki",
            "exhibitions-current", "exhibitions-traveling",
            "exhibitions-past", "exhibitions-virtual",
            "museum-exhibit-2026-10-05-ot-remesla-do-iskusstva-reznye-pryanichnye-doski",
            "museum-exhibit-2025-10-08-hleb-blokadnogo-goroda",
            "science-conferences","science-publications","science-collection",
            "science-researchers","science-materials",
            "science-organization","science-methodical-council",
            "science-seminar-2026-04-16-633",
            "museum-news-2026-10-16-noch-iskusstv-v-muzee-hleba",
            "museum-news-2026-10-12-sobytiya-v-muzee-s-12-po-19-oktyabrya"}


def run(command: list[str], cwd: Path, env: dict, log: Path) -> None:
    with log.open("a", encoding="utf-8") as stream:
        try:
            subprocess.run(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
        except subprocess.CalledProcessError:
            stream.flush()
            print("Isolated QA failed; last subprocess log lines:\n" +
                  "\n".join(log.read_text(errors="replace").splitlines()[-35:]), flush=True)
            raise


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
            if n != 97:
                raise RuntimeError("Private working CMS count changed: expected 97 drafts")
            sem=db.execute("select count(*) from museum_entries where slug like "
                           "'science-seminar-%' and status='draft'").fetchone()[0]
            if sem != 7:
                raise RuntimeError("All 7 genuine scientific seminar articles must be private")
            video_total = db.execute("select count(*) from museum_videos").fetchone()[0]
            if video_total != 0:
                raise RuntimeError("Real CMS must have zero invented/licence-unapproved videos")
            n = db.execute("select count(*) from museum_entries "
                           "where slug like 'museum-news-%' and type='news' and status='draft'").fetchone()[0]
            if n != 10:
                raise RuntimeError("All ten genuine current museum news records must remain private")
            event = db.execute("select status,starts_at from museum_events "
                               "where slug='museum-night-of-arts-2026'").fetchone()
            if event != ("draft","2026-11-03 00:00:00"):
                raise RuntimeError("Dated source event must remain unpublished with verified date: "+repr(event))
            n = db.execute("select count(*) from museum_events where slug like "
                           "'museum-session-%' and status='draft'").fetchone()[0]
            if n != 124:
                raise RuntimeError("Expected 124 true Sep–Oct weekly museum source event drafts, all unpublished")
            n = db.execute("select count(*) from museum_events "
                           "where status='draft'").fetchone()[0]
            if n != 125:
                raise RuntimeError("Expected 124 confirmed timed sessions + one Nov3 source event as drafts")
            n = db.execute("select count(*) from museum_entries where slug in "
                           "('science-organization','science-methodical-council') and status='draft'").fetchone()[0]
            if n != 2:
                raise RuntimeError("Two genuine scientific institutional source drafts must stay private")
            n = db.execute("select count(*) from museum_entries "
                           "where slug like 'museum-exhibit-%' and type='exhibition' and status='draft'").fetchone()[0]
            if n != 6:
                raise RuntimeError("All six real exhibition description drafts must remain private")

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
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes') "
                       "where slug in ('exhibitions-current','exhibitions-traveling',"
                       "'exhibitions-past','exhibitions-virtual')")
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes'),"
                       "title='QA: резные пряничные доски музея',"
                       "excerpt='QA: редакторская аннотация текущей выставки.',"
                       "body='<p>QA: утверждённая редакция выставки резных досок.</p>' "
                       "where slug='museum-exhibit-2026-10-05-ot-remesla-do-iskusstva-reznye-pryanichnye-doski'")
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes'),"
                       "title='QA: передвижной Хлеб блокадного города',"
                       "excerpt='QA: редакторский анонс выездной выставки.',"
                       "body='<p>QA: редакция выездной выставки о блокадном хлебе.</p>' "
                       "where slug='museum-exhibit-2025-10-08-hleb-blokadnogo-goroda'")
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes') "
                       "where slug in ('science-conferences','science-publications',"
                       "'science-collection','science-researchers','science-materials')")
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes'),"
                       "title='QA: редакторский научно-методический совет',"
                       "body='<p>QA: проверенная правка научного отдела музея.</p>' "
                       "where slug='science-methodical-council'")
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes'),"
                       "title='QA: музей отредактировал семинар о мельницах',"
                       "excerpt='QA: редактор уточнил научный семинар.',"
                       "body='<p>QA: проверенное описание семинара 16 апреля.</p>' "
                       "where slug='science-seminar-2026-04-16-633'")
            # QA-ONLY: one original museum-published VK recording with
            # fictional TEST transcript/rights created solely in disposable
            # SQLite. Never copied into real museum database or Git fixture.
            video_entry=db.execute("select id from museum_entries "
                "where slug='science-seminar-2026-04-16-633'").fetchone()[0]
            qa_transcript="QA: доступное текстовое описание музейного семинара. " * 3
            db.execute("insert into museum_videos (museum_entry_id,code,title,embed_url,"
                "source_url,transcript,rights_confirmed,status,created_at,updated_at) "
                "values (?, 'qa-editor-approved','QA: запись научного семинара',"
                "'https://vk.com/video_ext.php?oid=-37126776&id=456239157',"
                "'https://muzei-xleb.ru/seminar-k-istorii-mukomolnyh-melnic-v-rossii-16-aprelya-2026-g',"
                "?,1,'published',datetime('now'),datetime('now'))",
                (video_entry,qa_transcript))
            db.execute("update museum_entries set body="
                "'<p>QA: часть текста до ролика.</p><p>[[museum-video:qa-editor-approved]]</p>'"
                "||'<p>QA: часть текста после ролика.</p>' "
                "where id=?",(video_entry,))
            db.execute("update museum_entries set status='published',"
                       "published_at=datetime('now','-10 minutes'),"
                       "title='QA: Ночь искусств — редакция музея',"
                       "excerpt='QA: новый редакторский анонс Ночи искусств.',"
                       "body='<p>QA: утверждённая редактором новость 16 октября.</p>' "
                       "where slug='museum-news-2026-10-16-noch-iskusstv-v-muzee-hleba'")
            db.execute("update museum_events set status='published',"
                       "published_at=datetime('now','-10 minutes'),"
                       "title='QA: Ночь искусств 3 ноября — анонс редактора',"
                       "excerpt='QA: музей утвердил программу 3 ноября.',"
                       "body='<p>QA: музейная программа 18:00–20:00 в новой редакции.</p>' "
                       "where slug='museum-night-of-arts-2026'")
            db.execute("update museum_events set status='published',"
                       "published_at=datetime('now','-10 minutes'),"
                       "title='QA: Истинная экскурсия 18 октября — редакция музея',"
                       "excerpt='QA: сеанс 18 октября подтверждён музеем.',"
                       "body='<p>QA: редакторская версия на 18 октября 14:00.</p>' "
                       "where slug='museum-session-2026-10-18-1400-f7f11bc2731f'")
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
        approved_video=next(e for e in data["entries"] if e["slug"]=="science-seminar-2026-04-16-633")
        if len(approved_video.get("videos",[]))!=1:
            raise RuntimeError("Exactly one QA-original video must pass controlled CMS export")
        if approved_video["videos"][0]["code"]!="qa-editor-approved":
            raise RuntimeError("Video code corrupted in published CMS JSON")
        if not approved_video["videos"][0]["transcript"].startswith("QA: доступное текстовое описание"):
            raise RuntimeError("Video text alternative missing from published JSON")
        if any("rights_confirmed" in v for v in approved_video.get("videos",[])):
            raise RuntimeError("Unnecessary private licence-review status leaked into public CMS JSON")
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
        current_exhibition = html.fromstring(
            (out/"guide/exhibitions-current/index.html").read_bytes())
        traveling_exhibition = html.fromstring(
            (out/"guide/exhibitions-traveling/index.html").read_bytes())
        past_exhibition = html.fromstring(
            (out/"guide/exhibitions-past/index.html").read_bytes())
        virtual_exhibition = html.fromstring(
            (out/"guide/exhibitions-virtual/index.html").read_bytes())
        for name, doc, count in (
            ("current",current_exhibition,2),
            ("traveling",traveling_exhibition,4),
            ("past",past_exhibition,12),
            ("virtual",virtual_exhibition,12),
        ):
            if len(doc.xpath("//main//article[contains(@class,'official-museum-program-card')]")) != count:
                raise RuntimeError("Published CMS exhibition index "+name+" lost real source item count")
            if "Содержание, опубликованное редактором музея" not in doc.text_content():
                raise RuntimeError("Exhibition CMS index no longer editor-managed: "+name)
        if "3 октября – 7 декабря 2026 г." not in current_exhibition.text_content():
            raise RuntimeError("Original current exhibition date lost")
        if "QA: резные пряничные доски музея" not in current_exhibition.text_content():
            raise RuntimeError("CMS approved current exhibit did not override the source title")
        if "QA: передвижной Хлеб блокадного города" not in traveling_exhibition.text_content():
            raise RuntimeError("CMS approved traveling exhibit did not override the source title")
        for name, doc in (("current",current_exhibition),("traveling",traveling_exhibition)):
            links=doc.xpath("//main//section[contains(@class,'official-exhibitions')]"
                            "//a[starts-with(@href,'/exhibitions/')]")
            if len(links)!=1:
                raise RuntimeError("CMS exhibition "+name+" links to draft exhibits or lost editor entry")
        if not (out/"exhibitions/museum-exhibit-2026-10-05-ot-remesla-do-iskusstva-reznye-pryanichnye-doski/index.html").is_file():
            raise RuntimeError("Approved current source exhibition lacks public detail route")
        if (out/"exhibitions/museum-exhibit-2025-10-08-hleb-v-russkih-tradiciyah/index.html").is_file():
            raise RuntimeError("Unapproved traveling source draft was released")
        future=html.fromstring((out/"guide/exhibitions-future/index.html").read_bytes())
        if not future.xpath("//main//section[@aria-label='Будущие выставки из CMS']"):
            raise RuntimeError("Missing CMS-filtered future exhibitions section")
        future_section=future.xpath("//main//section[@aria-label='Будущие выставки из CMS']")[0]
        if "Выставка о хлебопечении" in future_section.text_content():
            raise RuntimeError("Precontract demo exhibition falsely appears in future exhibition section")
        science_slugs=[
            "science-conferences","science-publications","science-collection",
            "science-researchers","science-materials",
        ]
        for slug in science_slugs:
            page=html.fromstring((out/"guide"/slug/"index.html").read_bytes())
            if not page.xpath("//main//section[contains(@class,'museum-science-portal')]"):
                raise RuntimeError("Isolated CMS science section no longer rendered: "+slug)
            if "Содержание, опубликованное редактором музея" not in page.text_content():
                raise RuntimeError("Isolated CMS science landing draft not published: "+slug)
        science_materials=html.fromstring((out/"guide/science-materials/index.html").read_bytes())
        if "QA: редакторский научно-методический совет" not in science_materials.text_content():
            raise RuntimeError("Scientific original has not been replaced by editor-reviewed revision")
        if "QA: проверенная правка научного отдела музея" not in science_materials.text_content():
            raise RuntimeError("Scientific material CMS text override did not reach Next.js")
        if len(science_materials.xpath("//main//article[contains(@class,'official-museum-program-card')]"))!=2:
            raise RuntimeError("Two original scientific museum sources missing in CMS-fed catalogue")
        if len(science_materials.xpath("//main//a[starts-with(@href,'/museum/science-methodical-council/')]"))!=1:
            raise RuntimeError("Published scientific source detail link missing")
        if science_materials.xpath("//main//a[starts-with(@href,'/museum/science-organization/')]"):
            raise RuntimeError("Unpublished scientific organizational paper leaked as CMS route")
        if not (out/"museum/science-methodical-council/index.html").is_file():
            raise RuntimeError("Published scientific council detail page missing")
        if (out/"museum/science-organization/index.html").is_file():
            raise RuntimeError("Scientific concept unapproved source draft exposed")
        conference=html.fromstring((out/"guide/science-conferences/index.html").read_bytes())
        if "Подтверждённый" in conference.text_content() and "На действующем сайте" not in conference.text_content():
            raise RuntimeError("Scientific conference calendar implies nonexistent confirmed events")
        if "Не является действительной" in conference.text_content():
            raise RuntimeError("Irrelevant demo programme in science conference view")
        publication=html.fromstring((out/"guide/science-publications/index.html").read_bytes())
        if "Подтверждённая библиография" not in publication.text_content():
            raise RuntimeError("Scientific source PDF misclassified as published academic bibliography")
        collection=html.fromstring((out/"guide/science-collection/index.html").read_bytes())
        if "https://goskatalog.ru/portal/#/collections?museumIds=1200" not in collection.xpath("//main//a/@href"):
            raise RuntimeError("Exact original museum Goskatalog collection ID not preserved")
        researchers=html.fromstring((out/"guide/science-researchers/index.html").read_bytes())
        if "https://muzei-xleb.ru/sites/default/files/page/20260203112347-poryadok_dostupa.pdf" not in researchers.xpath("//main//a/@href"):
            raise RuntimeError("True museum rules for collection access not linked on researcher page")
        if researchers.xpath("//main//section[contains(@class,'museum-science-portal')]//form"):
            raise RuntimeError("Unverified researcher application form introduced")
        approved_science={e["slug"] for e in data["entries"] if e["slug"].startswith("science-seminar-")}
        if approved_science!={"science-seminar-2026-04-16-633"}:
            raise RuntimeError("Only one edited scientific seminar allowed publicly in isolated QA")
        science=html.fromstring((out/"guide/science-conferences/index.html").read_bytes())
        science_text=science.text_content()
        if "QA: музей отредактировал семинар о мельницах" not in science_text:
            raise RuntimeError("Real source seminar CMS editor override not shown on science landing")
        if "7 научных мероприятий 2020–2026 годов" not in science_text:
            raise RuntimeError("Seven genuine original museum dated science seminars absent")
        if not (out/"museum/science-seminar-2026-04-16-633/index.html").is_file():
            raise RuntimeError("Approved edited scientific seminar has no public detail route")
        if (out/"museum/science-seminar-2025-11-06-536/index.html").is_file():
            raise RuntimeError("Unpublished official seminar draft accidentally exported")
        seminar_page=html.fromstring((out/"museum/science-seminar-2026-04-16-633/index.html").read_bytes())
        if not seminar_page.xpath("//section[contains(@class,'museum-inline-video')]"):
            raise RuntimeError("Controlled inline museum VK player missing from published CMS page")
        if seminar_page.xpath("//section[contains(@class,'museum-inline-video')]//iframe"):
            raise RuntimeError("Passive VK iframe loaded before visitor explicitly opts in")
        if "QA: часть текста до ролика" not in seminar_page.text_content() or "QA: часть текста после ролика" not in seminar_page.text_content():
            raise RuntimeError("CMS TinyMCE inline video split lost surrounding genuine editor paragraphs")
        news=html.fromstring((out/"news/index.html").read_bytes())
        news_feed=news.xpath("//main//section[@aria-label='Последние новости действующего сайта музея']")
        if len(news_feed)!=1:
            raise RuntimeError("Ten original museum news feed lost during CMS release")
        cards=news_feed[0].xpath(".//article[contains(@class,'official-museum-program-card')]")
        if len(cards)!=10:
            raise RuntimeError("10 authentic news articles not shown in new site")
        if "QA: Ночь искусств — редакция музея" not in news_feed[0].text_content():
            raise RuntimeError("News editor title failed to override original source title")
        if "QA: утверждённая редактором новость 16 октября." not in news_feed[0].text_content():
            raise RuntimeError("News editor body failed to override original source text")
        approved_news={e['slug'] for e in data['entries']
                       if e['slug'].startswith('museum-news-')}
        if approved_news!={"museum-news-2026-10-16-noch-iskusstv-v-muzee-hleba"}:
            raise RuntimeError("Unpublished real museum news draft leaked")
        if not (out/"news/museum-news-2026-10-16-noch-iskusstv-v-muzee-hleba/index.html").is_file():
            raise RuntimeError("Published source-backed news not reachable on own detail route")
        if (out/"news/museum-news-2026-10-12-sobytiya-v-muzee-s-12-po-19-oktyabrya/index.html").is_file():
            raise RuntimeError("Draft museum weekly news gained unexpected public detail route")
        official_event={e['slug'] for e in data['events'] if e['slug'].startswith('museum-night-')}
        if official_event!={"museum-night-of-arts-2026"}:
            raise RuntimeError("One verified, edited Nov 3 event should be public only in isolated QA")
        events_html=html.fromstring((out/"events/index.html").read_bytes())
        if "QA: Ночь искусств 3 ноября — анонс редактора" not in events_html.text_content():
            raise RuntimeError("Editor-approved Nov 3 event absent from actual published CMS agenda")
        if events_html.xpath("//main//section[contains(@class,'official-source-event')]"):
            raise RuntimeError("News-source Night Arts teaser not suppressed when approved CMS event is available")
        event_detail=html.fromstring((out/"events/museum-night-of-arts-2026/index.html").read_bytes())
        if "QA: музейная программа 18:00–20:00 в новой редакции" not in event_detail.text_content():
            raise RuntimeError("Updated CMS event body not published in event detail route")
        session_entries={e['slug'] for e in data['events']
                         if e['slug'].startswith('museum-session-')}
        if session_entries!={"museum-session-2026-10-18-1400-f7f11bc2731f"}:
            raise RuntimeError("Only one edited verified source session may be public in isolated QA")
        session_page=html.fromstring((out/"events/museum-session-2026-10-18-1400-f7f11bc2731f/index.html").read_bytes())
        if "QA: редакторская версия на 18 октября 14:00." not in session_page.text_content():
            raise RuntimeError("Published official dated session missing editor-customized body")
        if (out/"events/museum-session-2026-10-18-1500-ddf212b58640/index.html").is_file():
            raise RuntimeError("Unapproved 15:00 museum session draft gained public URL")
        source_agenda=html.fromstring((out/"events/index.html").read_bytes())
        source_region=source_agenda.xpath("//main//section[@aria-label='Проверенные сеансы из официальных недельных афиш музея']")
        if len(source_region)!=1 or "124 отдельных сеанса" not in source_region[0].text_content():
            raise RuntimeError("Full 124 genuine weekly museum sessions source count missing")
        if "QA: Истинная экскурсия 18 октября — редакция музея" not in source_agenda.text_content():
            raise RuntimeError("CMS approved October 18 edited real session not shown")
        # Real browser check against the disposable published Next static site.
        # The server uses a dynamic localhost port and is stopped before
        # the isolated temporary QA filesystem is removed.
        handler=partial(SimpleHTTPRequestHandler, directory=str(out))
        server=ThreadingHTTPServer(("127.0.0.1",0),handler)
        thread=Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            url=f"http://127.0.0.1:{server.server_port}/"
            run(["node",str(WEB/"scripts/qa_editorial_video_browser.cjs"),url],
                WEB,environment,log)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
        # Source fallback is hydrated on the client; Playwright asserts its
        # exact suppression by slug after the CMS approval in browser tests.
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
    print("PASS: isolated approved museum source news (10 genuine current cards,"
          " one CMS-edited news item, 9 remaining unpublished news drafts),"
          " one editor-approved Nov 3 Night Arts event with exact original date"
          " and 18:00–20:00 program, no duplicate teaser upon CMS publication,"
          " five scientific categories/one council override, four exhibition"
          " categories/two edited exhibition details, two edited excursions,"
          " 12 master classes, 11 halls, nine FAQ, QA-only shop item,"
          " unchanged 44 original documents with SHA256;"
          " 124 real verified timed museum sessions across 6 weekly programmes,"
          " one genuine dated CMS-edited Oct18 session in isolated publication,"
          " 123 other source sessions private, 16 source overlap duplicates folded,"
          " 7 real dated scientific seminars and 16 associated original VK videos,"
          " one edited published only in isolated QA, six others private,"
          " real CMS remains 97 private draft entries, 125 private event drafts,"
          " 44 museum documents.")
    # Historical predecessor output deliberately superseded by current scope.
    # print("PASS: 23 isolated published CMS records including 12 real workshop cards"



if __name__ == "__main__":
    main()
