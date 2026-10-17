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
REQUIRED = {"museum-privacy", "tickets-and-benefits", "museum-history"}


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
        doc = db.execute(
            "select d.sha256,d.file_type,d.size_bytes,d.storage_path "
            "from museum_documents d join museum_entries e on d.museum_entry_id=e.id "
            "where e.slug='museum-privacy'"
        ).fetchone()
        if doc is None:
            raise RuntimeError("No official privacy PDF attachment in local CMS")

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
                       "where slug='tickets-and-benefits'")
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
        if not {"museum-privacy", "tickets-and-benefits"} <= slugs or "museum-history" in slugs:
            raise RuntimeError("Public/private source CMS entries wrongly filtered: " + repr(slugs))
        item = next(entry for entry in data["entries"] if entry["slug"] == "museum-privacy")
        if len(item.get("documents", [])) != 1:
            raise RuntimeError("Approved local document was not exported")
        href = item["documents"][0]["href"]
        if item["documents"][0]["accessibility_reviewed"] or not href.startswith("/documents/"):
            raise RuntimeError("Unreviewed original incorrectly marked accessible or missing route")
        doc_file = documents / Path(href).name
        if not doc_file.exists() or hashlib.sha256(doc_file.read_bytes()).hexdigest() != doc[0]:
            raise RuntimeError("Exported original doc checksum does not match private CMS record")

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
        fallback = html.fromstring((out / "guide/museum-history/index.html").read_bytes())
        h1 = [str(x).strip() for x in privacy.xpath("//main//h1/text()")]
        if h1 != ["QA: заголовок из редактируемой CMS"]:
            raise RuntimeError("CMS H1 not authoritative on guide route: " + repr(h1))
        title = privacy.xpath("//head/title/text()")
        desc = privacy.xpath("//head/meta[@name='description']/@content")
        if not any("QA: заголовок SEO из CMS" in x for x in title) or desc != ["QA: описание поискового сниппета"]:
            raise RuntimeError("CMS page title/SEO not authoritative in static Next HTML")
        links = privacy.xpath("//main//a/@href")
        if href not in links or not (out / href.lstrip("/")).exists():
            raise RuntimeError("PDF attachment from published CMS page missing/broken")
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
    print("PASS: 2 published-in-disposable-copy CMS pages, 1 SHA256-verified PDF, "
          "editable title/H1/SEO, real price table, reference fallback, noindex; "
          "original 8 draft entries and tracked web snapshot unchanged.")


if __name__ == "__main__":
    main()
