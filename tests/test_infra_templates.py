import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InfraTemplateTests(unittest.TestCase):
    def test_public_nginx_must_not_expose_backend(self):
        config = (ROOT / "infra/nginx/public-static.conf").read_text()
        self.assertIn("127.0.0.1:18080", config)
        self.assertNotIn("fastcgi_pass", "\n".join(line for line in config.splitlines() if not line.lstrip().startswith("#")))
        self.assertNotIn("proxy_pass", "\n".join(line for line in config.splitlines() if not line.lstrip().startswith("#")))
        self.assertIn("return 404;", config)
        self.assertIn("root /srv/musbread/public/current", config)
        self.assertIn("include /etc/nginx/musbread-csp.conf;", config)
        # A location-level add_header would silently mask inherited CSP.
        for section in config.split("location /_next/static/")[1:]:
            self.assertNotIn("add_header", "\n".join(
                line for line in section.split("location /media/")[0].splitlines()
                if not line.strip().startswith("#")
            ))

    def test_private_cms_is_loopback_and_uses_php_fpm(self):
        config = (ROOT / "infra/nginx/private-cms.conf").read_text()
        self.assertIn("listen 127.0.0.1:18082;", config)
        self.assertIn("fastcgi_pass unix:/run/php/php8.4-fpm.sock;", config)
        self.assertIn("client_max_body_size 6m;", config)
        self.assertIn("limit_req zone=musbread_auth burst=5 nodelay;", config)
        self.assertIn("limit_req zone=musbread_upload burst=15 nodelay;", config)
        self.assertIn("frame-ancestors 'none'", config)
        # Private MoonShine uses public/vendor for its runtime assets, but
        # Composer code/docs and any other vendor trees must be 404.
        self.assertIn("location ~ ^/vendor/(moonshine|museum-jodit)/",config)
        self.assertIn("location ~ ^/(storage|database|bootstrap|vendor)/ { return 404; }",config)
        self.assertLess(config.index("location ~ \\.php$"),
                        config.index("location ~ ^/vendor/(moonshine"))
        self.assertLess(config.index("location ~ /\\."),
                        config.index("location ~ ^/vendor/(moonshine"))
        rates = (ROOT / "infra/nginx/http-rates.conf").read_text()
        self.assertIn("map $request_method $musbread_write_ip", rates)
        self.assertIn("POST $binary_remote_addr;", rates)
        self.assertIn("rate=8r/m", rates)
        self.assertIn("rate=30r/m", rates)

    def test_worker_timeout_must_be_lower_than_retry_window(self):
        queue = (ROOT / "infra/systemd/musbread-publisher.service").read_text()
        self.assertIn("--timeout=540", queue)
        self.assertIn("--queue=museum-publish", queue)
        config = (ROOT / "apps/cms/config/queue.php").read_text()
        self.assertIn("DB_QUEUE_RETRY_AFTER', 900", config)
        self.assertIn("NoNewPrivileges=true", queue)
        self.assertIn("ProtectSystem=strict", queue)

    def test_publisher_fails_closed_on_bad_queue_and_recovers_from_clean_exit(self):
        unit = (ROOT / "infra/systemd/musbread-publisher.service").read_text()
        self.assertIn(
            "ExecStartPre=/usr/bin/php8.4 artisan museum:cache-check --require-shared --require-queue-worker",
            unit,
        )
        self.assertIn("Restart=always", unit)
        self.assertIn("StartLimitBurst=5", unit)
        self.assertIn("UMask=0027", unit)
        self.assertIn("ProtectSystem=strict", unit)
        self.assertIn("--timeout=540", unit)
        self.assertNotIn("--timeout=900", unit)
        queue_docs = (ROOT / "docs/PUBLICATION_QUEUE.md").read_text()
        self.assertIn("timeout=540", queue_docs)
        self.assertIn("DB_QUEUE_RETRY_AFTER=900", queue_docs)
        self.assertIn("systemd/musbread-scheduler.timer", queue_docs)

    def test_php_fpm_gate_is_not_a_cli_version_check(self):
        script = (ROOT / "scripts/check_php_fpm.py").read_text()
        self.assertIn("fpm-fcgi", script)
        self.assertIn("nginx_template", script)
        self.assertIn("expected_listen", script)
        nginx = (ROOT / "infra/nginx/private-cms.conf").read_text()
        self.assertIn("fastcgi_pass unix:/run/php/php8.4-fpm.sock", nginx)
        self.assertNotIn("proxy_pass", nginx)
        self.assertIn("UMask=0027",
            (ROOT / "infra/systemd/musbread-scheduler.service").read_text())

    def test_public_nginx_rejects_nonpublic_folders_even_if_copied_accidentally(self):
        text = (ROOT / "infra/nginx/public-static.conf").read_text()
        for blocked in ("admin", "api", "vendor", "storage", "database", "bootstrap", "config", "private"):
            self.assertIn(blocked, text.split("location ~* ^/(")[1].split(")(/|$)")[0])
        self.assertIn("location ~* \\.(php|phtml|phar|cgi|env|sql|sqlite|bak|log)", text)

    def test_scheduler_uses_systemd_timer(self):
        timer = (ROOT / "infra/systemd/musbread-scheduler.timer").read_text()
        self.assertIn("OnCalendar=*-*-* *:*:00", timer)
        self.assertIn("Unit=musbread-scheduler.service", timer)


if __name__ == "__main__":
    unittest.main()
