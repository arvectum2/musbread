#!/usr/bin/env python3
"""Fail-closed MusBread release preflight. OFFLINE by default; never deploys.

Production checks use HTTPS only when --live-url is explicitly provided.
The current staging build must remain noindex; a production site must not.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import release_site as releases


class PreflightError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise PreflightError(message)


def verify_staging_seo(out: Path) -> dict:
    require(out.is_dir() and not out.is_symlink(), 'Static output is missing or a symlink')
    root = (out / 'index.html')
    require(root.is_file() and not root.is_symlink(), 'Missing public index.html')
    robots = (out / 'robots.txt').read_text(encoding='utf-8')
    sitemap = (out / 'sitemap.xml').read_text(encoding='utf-8')
    require(bool(re.search(r'(?im)^Disallow:\s*/\s*$', robots)), 'Staging robots must block all crawling')
    require('<url>' not in sitemap and '<urlset' in sitemap, 'Staging sitemap must be empty')
    require(not any(out.rglob('.musbread-legacy-alias')), 'Private build marker in static output')
    return {'mode': 'preaward_noindex', 'index_html': True, 'robots_blocks': True, 'empty_sitemap': True}


def verify_nginx_template(path: Path) -> dict:
    s = path.read_text(encoding='utf-8')
    for token in ('root /srv/musbread/public/current;', 'server_tokens off;',
                  'X-Content-Type-Options', 'include /etc/nginx/musbread-csp.conf;',
                  'location /documents/', 'location /_next/static/', 'try_files $uri'):
        require(token in s, 'Missing public Nginx protection: '+token)
    for bad in ('proxy_pass ', 'fastcgi_pass '):
        require(bad not in s, 'Public static contour must not forward dynamic backend requests')
    return {'static_only': True, 'security_headers': True, 'csp_required': True}


def rehearse_rollback(working_dir: Path) -> dict:
    """Exercise REAL public release functions in isolated synthetic fixtures."""
    working_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='preflight-rollback-', dir=working_dir) as tmp:
        base = Path(tmp)
        site = base / 'site'; site.mkdir()
        snapshot = base / 'private.json'; snapshot.write_bytes(b'{"events":[]}\n')
        manifest = base / 'manifest.json'
        manifest.write_text(json.dumps({'files': {'published.json': {
            'sha256': hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            'bytes': snapshot.stat().st_size,
        }}}), encoding='utf-8')
        dest = base / 'release'
        (site / 'index.html').write_text('release-A', encoding='utf-8')
        a = releases.prepare(site, snapshot, manifest, dest)
        (site / 'index.html').write_text('release-B', encoding='utf-8')
        b = releases.prepare(site, snapshot, manifest, dest)
        require(a != b and (dest / 'current/index.html').read_text() == 'release-B', 'Release switching failed')
        require(releases.rollback(dest) == a, 'Rollback pointer wrong')
        require((dest / 'current/index.html').read_text() == 'release-A', 'Rollback content wrong')
        require(releases.history(dest)['previous'] == b, 'Recovery target not preserved')
        return {'isolated_rehearsal': 'PASS', 'prior_release_restored': True, 'no_production_writes': True}


def verify_existing_release(root: Path) -> dict:
    """Read-only check: existing current/previous must be intact and switchable."""
    require(root.is_dir() and not root.is_symlink(), 'Release root missing or symlink')
    require(not (root / '.release-transition.json').exists(), 'Interrupted release transition, recover first')
    ids = {}
    for role in ('current', 'previous'):
        ident = releases._release_pointer_id(root, role)
        require(ident is not None, 'Missing '+role+' release; rollback not available')
        require(releases.validate_release(root / 'releases' / ident) == ident, 'Bad '+role+' checksum')
        ids[role] = ident
    require(ids['current'] != ids['previous'], 'No distinct previous rollback target')
    return ids


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def get_https(url: str, timeout: int = 12) -> tuple[int, bytes, dict]:
    """Verify TLS >=1.2 and hostname with standard trust store. No auto redirects."""
    parts = urlsplit(url)
    require(parts.scheme == 'https' and parts.hostname and not parts.username and not parts.password,
            'Production probe accepts verified HTTPS URLs only')
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    opener = build_opener(HTTPSHandler(context=context), NoRedirect())
    try:
        with opener.open(Request(url, headers={'User-Agent': 'MusBread-ReadOnly-Release-Preflight/1'}),
                         timeout=timeout) as response:
            return response.status, response.read(1_000_001), dict(response.headers)
    except HTTPError as error:
        try:
            return error.code, error.read(1_000_001), dict(error.headers)
        finally:
            error.close()


def sample_redirects(path: Path, count: int = 4) -> list[tuple[str, str]]:
    """Use source-verified mapping only; never invent old museum URL targets."""
    require(path.is_file(), 'Generated legacy Nginx redirect map is missing')
    rows = re.findall(r'^\s*(/\S+)\s+"(/[^"\s]+)";', path.read_text(encoding='utf-8'), re.M)
    require(len(rows) >= count, 'Legacy redirect map too short')
    pages = [p for p in rows if not p[0].startswith('/sites/default/files/')]
    assets = [p for p in rows if p[0].startswith('/sites/default/files/')]
    choices = pages[:max(1, count // 2)] + assets[:count - max(1, count // 2)]
    require(len(choices) == count, 'Not enough mixed original page + asset redirects')
    return choices


def verify_live_site(base: str, mappings: list[tuple[str, str]], fetch=get_https) -> dict:
    parts = urlsplit(base)
    require(parts.scheme == 'https' and bool(parts.hostname) and not parts.path.strip('/')
            and not parts.query and not parts.fragment and not parts.username and not parts.password,
            'Expected --live-url https://approved-host (no path, query, credentials)')
    origin = 'https://' + parts.netloc
    index_status, index, root_headers = fetch(origin+'/')
    require(index_status == 200 and b'<html' in index.lower(), 'Production homepage not HTTP 200 HTML')
    headers = {str(k).lower(): str(v) for k, v in root_headers.items()}
    require(headers.get('x-content-type-options', '').lower() == 'nosniff', 'Missing X-Content-Type-Options')
    require(bool(headers.get('content-security-policy')), 'Missing Content-Security-Policy')
    require(len(headers['content-security-policy'].encode('utf-8')) <= 8192,
            'Content-Security-Policy response header exceeds conservative 8 KiB limit; use per-route hashes, never disable CSP')
    require(bool(headers.get('strict-transport-security')), 'Missing TLS HSTS policy')
    require('noindex' not in headers.get('x-robots-tag','').lower(), 'Production X-Robots-Tag blocks indexing')
    robots_status, robots, _ = fetch(origin+'/robots.txt')
    require(robots_status == 200 and not re.search(rb'(?im)^disallow:\s*/\s*$', robots), 'Production robots still block indexing')
    sitemap_status, sitemap, _ = fetch(origin+'/sitemap.xml')
    require(sitemap_status == 200 and b'<url>' in sitemap, 'Production sitemap is empty or unavailable')
    # Domain migration must not emit canonical references to pre-award aliases.
    require(b'noindex' not in index.lower(), 'Production homepage is marked noindex')
    require(parts.hostname.encode() in sitemap, 'Sitemap contains no approved canonical host')
    for old, expected in mappings:
        status, _, headers = fetch(origin+old)
        require(status == 301, f'Old museum path not HTTP 301: {old}: {status}')
        actual = urlsplit(urljoin(origin, headers.get('Location', headers.get('location', ''))))
        require(actual.scheme == 'https' and actual.netloc == parts.netloc and actual.path == urlsplit(expected).path,
                f'Wrong redirect target for old path {old}')
    return {'tls_minimum': '1.2', 'hostname_verified': True, 'homepage': 200,
            'robots_indexable': True, 'sitemap_nonempty': True, 'security_headers': True, 'redirect_samples': len(mappings)}


def run(args: argparse.Namespace) -> dict:
    from build_complete_museum_static_release import verify as verify_full
    require(args.output.resolve() == (ROOT/'apps/web/out').resolve(),
            'Full inventory check only supports the canonical repository static output')
    verify_full()  # Existing 945-page full link/doc/photo checksum gate.
    checks = {
        'static_inventory': 'PASS',
        'staging_seo': verify_staging_seo(args.output),
        'nginx_template': verify_nginx_template(ROOT/'infra/nginx/public-static.conf'),
        'rollback': rehearse_rollback(ROOT/'.local_archive'),
    }
    if args.release_root:
        checks['existing_release'] = verify_existing_release(args.release_root)
    if args.live_url:
        checks['live_site'] = verify_live_site(
            args.live_url, sample_redirects(ROOT/'deploy/nginx/legacy_museum_redirects.map.conf'))
    return {'status': 'PASS', 'scope': 'READ_ONLY_OFFLINE' if not args.live_url else 'LIVE_READ_ONLY_APPROVED_HOST',
            'NOT_PRODUCTION_ACCEPTANCE': True, 'checks': checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'apps/web/out')
    parser.add_argument('--release-root', type=Path, help='Existing release history; read-only SHA and rollback readiness check')
    parser.add_argument('--live-url', help='Explicitly approved HTTPS production hostname; read-only requests only')
    args = parser.parse_args()
    try:
        print('MUSBREAD_PREFLIGHT '+json.dumps(run(args), ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as error:
        print('MUSBREAD_PREFLIGHT '+json.dumps({'status': 'FAIL', 'error_type': type(error).__name__,
           'reason': str(error)[:240]}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
