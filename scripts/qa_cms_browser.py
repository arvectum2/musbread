#!/usr/bin/env python3
"""Isolated browser E2E of private MoonShine CMS; never alters the developer DB.

Creates a temporary SQLite file and ephemeral QA credentials, starts PHP bound
to loopback, tests a real browser, and deletes the DB/server automatically.
"""
import base64
import hashlib
import json
import os
import shutil
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
CMS = ROOT / "apps" / "cms"
WEB = ROOT / "apps" / "web"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def verify_browser_created_static_site(workspace: Path, published: Path,
                                       manifest: Path, media: Path,
                                       env: dict[str, str]) -> None:
    """Build Next.js from the *actual browser-created* CMS snapshot in a disposable tree.

    Never replace the tracked developer fixture or touch the normal Next.js build.
    npm dependencies are reused through a symlink; no second npm install or Docker.
    """
    isolated_web = workspace / "web-build"
    shutil.copytree(
        WEB, isolated_web,
        ignore=shutil.ignore_patterns("node_modules", ".next", "out",
                                      "test-results", "playwright-report"),
    )
    (isolated_web / "node_modules").symlink_to(WEB / "node_modules",
                                                target_is_directory=True)
    shutil.copyfile(published, isolated_web / "src/data/published.json")
    shutil.copyfile(manifest, isolated_web / "public/snapshot-manifest.json")
    if media.exists():
        shutil.copytree(media, isolated_web / "public/media", dirs_exist_ok=True)
    build_env = dict(env)
    build_env["NEXT_TELEMETRY_DISABLED"] = "1"
    print("Building isolated Next.js from browser-created CMS content", flush=True)
    run(["npm", "run", "build", "--", "--webpack"], isolated_web, build_env)

    out = isolated_web / "out"
    expected_paths = [
        (out / "events/qa-browser-event/index.html", "QA: музейное событие из браузера"),
        (out / "news/qa-browser-news/index.html", "QA: публикация из настоящего браузера"),
    ]
    for path, expected in expected_paths:
        if not path.is_file() or expected not in path.read_text(encoding="utf-8"):
            raise RuntimeError("Browser-created CMS record missing from static HTML: " + str(path))

    # TZ-233: metadata, visible H1 and description MUST survive the genuine
    # MoonShine form -> SQLite -> exporter -> Next static HTML journey.
    event_html = (out / "events/qa-browser-event/index.html").read_text(encoding="utf-8")
    section_page = out / "guide/qa-tree-root/index.html"
    if not section_page.exists():
        raise RuntimeError("CMS section route absent from generated static build")
    section_html = section_page.read_text(encoding="utf-8")
    for html, values in (
        (event_html, ("QA: META TITLE СОБЫТИЯ", "QA: META DESCRIPTION СОБЫТИЯ",
                      "QA: H1 посетителю — музейное событие")),
        (section_html, ("QA: META TITLE РАЗДЕЛА", "QA: META DESCRIPTION РАЗДЕЛА",
                        "QA: H1 раздела из CMS")),
    ):
        if not all(value in html for value in values):
            raise RuntimeError("TZ-233 approved CMS SEO fields missing from generated HTML")
        if "<meta name=\"robots\" content=\"noindex" not in html:
            raise RuntimeError("Pre-award HTML must remain non-indexable even with SEO fields")

    if (out / "events/qa-private-draft/index.html").exists():
        raise RuntimeError("Private browser-created draft was exported into the public website")
    news = (out / "news/qa-browser-news/index.html").read_text(encoding="utf-8")
    event = (out / "events/qa-browser-event/index.html").read_text(encoding="utf-8")
    if ('/excursions/demo-tour/' not in news or '/events/qa-browser-event/' not in news
            or 'qa-browser-news' not in event or '/news/qa-browser-news/' not in event):
        raise RuntimeError("Public content relations not rendered in real static HTML")
    if 'qa-private-draft' in news or 'qa-private-draft' in event:
        raise RuntimeError("Draft event relation leaked into published static HTML")
    # TZ-136: media hub must link ONLY already-published images and entries,
    # never raw private CMS paths or unpublished/draft files.
    media_hub_path = out / "guide/museum-media/index.html"
    if not media_hub_path.is_file():
        raise RuntimeError("Museum media route was not built")
    media_hub = media_hub_path.read_text(encoding="utf-8")
    if ('QA: экспонат на тестовом изображении' not in media_hub
            or '/news/qa-browser-news/' not in media_hub
            or 'qa-private-draft' in media_hub
            or 'museum/media/' in media_hub):
        raise RuntimeError("Published-only media hub is missing the QA image or leaks private paths")

    for asset in (item for item in media.glob("*.webp")):
        public_file = out / "media" / asset.name
        if not public_file.is_file() or hashlib.sha256(public_file.read_bytes()).hexdigest() != hashlib.sha256(asset.read_bytes()).hexdigest():
            raise RuntimeError("Browser-uploaded media missing or modified by static release")

    print("Verified UI-created news/event/section with SEO title, description and H1 in static HTML; draft excluded", flush=True)


def main() -> int:
    if (CMS / "bootstrap/cache/config.php").exists():
        raise RuntimeError("Cached Laravel config detected; refusing isolated QA")

    php = "/opt/homebrew/opt/php@8.4/bin/php"
    if not Path(php).is_file():
        php = "php"  # CI Linux

    port = free_port()
    with tempfile.TemporaryDirectory(prefix="musbread-qa-") as workspace:
        root = Path(workspace)
        db = root / "qa.sqlite"
        db.touch()
        qa_image = root / "qa-image.png"
        env = dict(os.environ)
        env.update({
            "APP_ENV": "testing",
            "APP_DEBUG": "false",
            "APP_KEY": "base64:" + base64.b64encode(secrets.token_bytes(32)).decode(),
            "APP_URL": "http://127.0.0.1:" + str(port),
            "DB_CONNECTION": "sqlite",
            "DB_DATABASE": str(db),
            "DB_URL": "",
            "SESSION_DRIVER": "database",
            "CACHE_STORE": "database",
            "QUEUE_CONNECTION": "sync",
            "MAIL_MAILER": "array",
            "MUSBREAD_E2E_USERNAME": "e2e@qa.musbread.invalid",
            "MUSBREAD_E2E_PASSWORD": secrets.token_urlsafe(28),
            "MUSBREAD_E2E_BASE_URL": "http://127.0.0.1:" + str(port),
            "MUSBREAD_E2E_IMAGE_PATH": str(qa_image),
        })
        run([php, "-r", "imagepng(imagecreatetruecolor(120, 80), getenv('MUSBREAD_E2E_IMAGE_PATH'));"],
            CMS, env)
        print("Preparing temporary QA database (never the developer DB)", flush=True)
        run([php, "artisan", "migrate", "--force", "--no-ansi"], CMS, env)
        run([php, "artisan", "db:seed", "--class=IsolatedBrowserQaSeeder", "--force", "--no-ansi"], CMS, env)
        run([php, "artisan", "db:seed", "--class=DemoMuseumContentSeeder", "--force", "--no-ansi"], CMS, env)
        # CP-44D: a PRIVATE immutable baseline from the seeded CMS, not
        # a live deployment or the developer's normal release/current pointer.
        baseline = root / "baseline-published.json"
        baseline_manifest = root / "baseline-manifest.json"
        run([php, "artisan", "museum:export",
             "--output=" + str(baseline),
             "--manifest=" + str(baseline_manifest),
             "--media-output-dir=" + str(root / "baseline-media"),
             "--document-output-dir=" + str(root / "baseline-documents")], CMS, env)
        sha = hashlib.sha256(baseline.read_bytes()).hexdigest()
        release_root = root / "release-fixture"
        release_files = {
            "index.html": hashlib.sha256(b"private QA release fixture").hexdigest(),
            "snapshot-manifest.json": hashlib.sha256(baseline_manifest.read_bytes()).hexdigest(),
        }
        release_id = hashlib.sha256(json.dumps(release_files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
        release_dir = release_root / "releases" / release_id
        release_dir.mkdir(parents=True)
        private = release_root / "private-snapshots"
        private.mkdir(mode=0o700)
        shutil.copyfile(baseline, private / (sha + ".json"))
        shutil.copyfile(baseline_manifest, release_dir / "snapshot-manifest.json")
        (release_dir / "index.html").write_bytes(b"private QA release fixture")
        (release_dir / "release-manifest.json").write_text(json.dumps({
            "release": release_id, "files": release_files,
        }), encoding="utf-8")
        (release_root / "current").symlink_to(Path("releases") / release_id)
        env["MUSEUM_LOCAL_RELEASE_ROOT"] = str(release_root)
        with (root / "server.log").open("wb") as logfile:
            server = subprocess.Popen(
                [php, "artisan", "serve", "--host=127.0.0.1", "--port=" + str(port), "--no-reload"],
                cwd=CMS, env=env, stdout=logfile, stderr=subprocess.STDOUT,
            )
            try:
                for _ in range(80):
                    if server.poll() is not None:
                        raise RuntimeError("QA PHP server stopped unexpectedly")
                    try:
                        with urlopen(env["MUSBREAD_E2E_BASE_URL"] + "/admin/login", timeout=0.6) as response:
                            if response.status == 200:
                                break
                    except (URLError, OSError, TimeoutError):
                        pass
                    time.sleep(0.25)
                else:
                    raise RuntimeError("QA PHP server failed readiness")
                print("Running isolated MoonShine browser smoke tests against loopback", flush=True)
                run(["npm", "run", "test:cms"], WEB, env)
                output = root / "published.json"
                manifest = root / "manifest.json"
                media_folder = root / "media"
                run([php, "artisan", "museum:export",
                     "--output=" + str(output), "--manifest=" + str(manifest),
                     "--media-output-dir=" + str(media_folder)], CMS, env)
                snapshot = json.loads(output.read_text(encoding="utf-8"))
                event_slugs = {item["slug"] for item in snapshot["events"]}
                if "qa-browser-event" not in event_slugs or "qa-private-draft" in event_slugs:
                    raise RuntimeError("UI-created event not exported or draft leaked")
                news = next((item for item in snapshot['entries'] if item['slug'] == 'qa-browser-news'), None)
                qa_event = next((item for item in snapshot['events'] if item['slug'] == 'qa-browser-event'), None)
                if not news or not qa_event:
                    raise RuntimeError("UI-created news or event missing from linked export")
                if '/excursions/demo-tour/' not in [link['href'] for link in news.get('related_entries', [])]:
                    raise RuntimeError("Browser-linked excursion missing from public JSON")
                if [link['href'] for link in news.get('related_events', [])] != ['/events/qa-browser-event/']:
                    raise RuntimeError("Draft-linked event leaked or public relation missing")
                if '/news/qa-browser-news/' not in [link['href'] for link in qa_event.get('related_entries', [])]:
                    raise RuntimeError("Reverse related-news link missing on the event")
                assets = [item for entry in snapshot["entries"] for item in entry.get("media", [])]
                if not any(item["alt"] == "QA: экспонат на тестовом изображении" for item in assets):
                    raise RuntimeError("Uploaded QA image missing from CMS export")
                audit = json.loads(manifest.read_text(encoding="utf-8"))
                for asset in assets:
                    path = media_folder / Path(asset["src"]).name
                    if not path.exists():
                        raise RuntimeError("Missing QA media output")
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    if audit["files"]["media/" + path.name]["sha256"] != digest:
                        raise RuntimeError("QA exported media checksum mismatch")
                verify_browser_created_static_site(root, output, manifest, media_folder, env)
                print("Verified browser-created event, article, image; draft excluded from public export", flush=True)
            except Exception:
                print("QA server output tail (without login credentials):", flush=True)
                print((root / "server.log").read_text(errors="replace")[-2500:], flush=True)
                raise
            finally:
                server.terminate()
                try:
                    server.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
        print("QA server closed; temporary database and account deleted", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (subprocess.CalledProcessError, RuntimeError) as exc:
        print(type(exc).__name__ + ": isolated browser QA failed", file=sys.stderr)
        sys.exit(1)
