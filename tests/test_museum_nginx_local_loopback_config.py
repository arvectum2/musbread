"""Prevent regressions in the real Nginx fixes from CP-SEO-06.

Structural checks run without Docker; the full HTTP suite is separately
replayed by scripts/verify_museum_nginx_loopback.sh on Mac mini localhost.
"""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class LocalRealMuseumNginxSafetyTests(unittest.TestCase):
    def test_local_conf_includes_real_long_url_map_hash_fixes_and_both_original_query_maps(self):
        s=(ROOT/'deploy/nginx/museum_local_loopback.conf').read_text()
        self.assertIn('map_hash_bucket_size 256;',s)
        self.assertIn('map_hash_max_size 8192;',s)
        self.assertIn('legacy_museum_redirects.map.conf;',s)
        self.assertIn('museum_news_original_query_pages.map.conf;',s)
        self.assertIn('legacy_museum_redirects.server.conf;',s)
        self.assertIn('museum_news_original_query_pages.server.conf;',s)
        self.assertIn('location / { try_files $uri/index.html $uri $uri/ =404; }',s)
        self.assertIn('absolute_redirect off;',s)
        self.assertIn('port_in_redirect off;',s)
        self.assertIn('server_name_in_redirect off;',s)
        self.assertIn('X-Musbread-Local-Test',s)
        self.assertNotIn('listen 443',s)
        self.assertNotIn('ssl_certificate',s)

    def test_replay_script_only_binds_loopback_and_auto_removes_the_container(self):
        s=(ROOT/'scripts/verify_museum_nginx_loopback.sh').read_text()
        self.assertIn('-p "127.0.0.1:$PORT:8080"',s)
        self.assertIn('trap cleanup EXIT INT TERM',s)
        self.assertIn('docker stop "$NAME"',s)
        self.assertIn('docker run --rm',s)
        self.assertIn('--mount "type=bind,source=$ROOT/apps/web/out,target=/srv/musbread,readonly"',s)
        self.assertIn('--entrypoint nginx',s)
        self.assertIn('"$IMAGE" -t',s)
        self.assertIn('audit_museum_nginx_http_loopback.py',s)
        self.assertNotIn('docker compose up',s)

    def test_real_http_audit_covers_full_corpus_and_requires_server_isolation(self):
        s=(ROOT/'scripts/audit_museum_nginx_http_loopback.py').read_text()
        self.assertIn("HOST='127.0.0.1'",s)
        self.assertIn("x-musbread-local-test",s)
        for count in ['881','467','101','303','28']:
            self.assertIn(count,s)

    def test_deployment_instructions_contain_tested_fix_without_claiming_prod_go(self):
        s=(ROOT/'deploy/nginx/README.md').read_text()
        self.assertIn('map_hash_bucket_size 256;',s)
        self.assertIn('map_hash_max_size 8192;',s)
        self.assertIn('absolute_redirect off;',s)
        self.assertIn('port_in_redirect off;',s)
        self.assertIn('server_name_in_redirect off;',s)
        self.assertIn('NO-GO',s)
        self.assertIn('CP_SEO_06_REAL_NGINX_LOOPBACK_20261019.md',s)

if __name__=='__main__':unittest.main()
