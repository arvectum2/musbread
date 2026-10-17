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
REQUIRED = {"museum-privacy", "tickets-and-benefits", "ticket-refunds", "museum-history", "museum-documents"}


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
            for slug in ("museum-privacy", "ticket-refunds", "museum-documents", "tickets-and-benefits")
        }
        expected_counts = {"museum-privacy": 2, "ticket-refunds": 2,
                           "museum-documents": 19, "tickets-and-benefits": 1}
        if any(len(expected_docs[slug]) != count for slug,count in expected_counts.items()):
            raise RuntimeError("Missing imported official documents or compressed copies in CMS")

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
                       "where slug in ('tickets-and-benefits','ticket-refunds','museum-documents')")
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
        if not {"museum-privacy", "tickets-and-benefits", "ticket-refunds", "museum-documents"} <= slugs or "museum-history" in slugs:
            raise RuntimeError("Public/private source CMS entries wrongly filtered: " + repr(slugs))
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
        fallback = html.fromstring((out / "guide/museum-history/index.html").read_bytes())
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
    print("PASS: 4 disposable published CMS pages, 24 SHA256-verified static files "
          "(including two compressed 42/45-page scanned originals, refund PDF and DOCX), "
          "editorial H1/SEO, prices, draft fallback, no PII forms, noindex; "
          "original 11 draft entries/41 documents and tracked web snapshot unchanged.")


if __name__ == "__main__":
    main()
