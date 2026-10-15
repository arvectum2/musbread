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

    def test_private_cms_is_loopback_and_uses_php_fpm(self):
        config = (ROOT / "infra/nginx/private-cms.conf").read_text()
        self.assertIn("listen 127.0.0.1:18082;", config)
        self.assertIn("fastcgi_pass unix:/run/php/php8.4-fpm.sock;", config)
        self.assertIn("client_max_body_size 6m;", config)

    def test_worker_timeout_must_be_lower_than_retry_window(self):
        queue = (ROOT / "infra/systemd/musbread-publisher.service").read_text()
        self.assertIn("--timeout=600", queue)
        self.assertIn("--queue=museum-publish", queue)
        config = (ROOT / "apps/cms/config/queue.php").read_text()
        self.assertIn("DB_QUEUE_RETRY_AFTER', 900", config)
        self.assertIn("NoNewPrivileges=true", queue)
        self.assertIn("ProtectSystem=strict", queue)

    def test_scheduler_uses_systemd_timer(self):
        timer = (ROOT / "infra/systemd/musbread-scheduler.timer").read_text()
        self.assertIn("OnCalendar=*-*-* *:*:00", timer)
        self.assertIn("Unit=musbread-scheduler.service", timer)


if __name__ == "__main__":
    unittest.main()
