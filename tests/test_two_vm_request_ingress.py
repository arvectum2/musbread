#!/usr/bin/env python3
"""Fail-closed architectural gates for the TWO-VM visitor intake, synthetic only."""
import json
import os
import re
import sqlite3
import socket
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
def source(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class TwoVmIntakeTests(unittest.TestCase):
    def test_only_two_vms_and_no_unapproved_public_backend(self):
        c=json.loads(source("docs/architecture/visitor-interactions.v1.json"))
        public, req=c["public"], c["requests"]
        self.assertFalse(public["stores_personal_data"])
        self.assertFalse(public["can_contact_cms_or_db"])
        self.assertFalse(public["accepts_post"])  # public STATIC APP, exact Nginx exception only
        self.assertFalse(req["live_enabled"])
        ingress=req["ingress"]
        self.assertTrue(ingress["no_extra_virtual_machine"])
        self.assertTrue(ingress["proxy_exception_requires_customer_approval"])
        self.assertTrue(ingress["private_worker_loopback_mtls"])
        self.assertEqual(ingress["host_role"],"private-vm-dedicated-restricted-php-fpm")

    def test_public_nginx_mtls_exact_post_not_cms(self):
        public=source("infra/nginx/two-vm-public-requests.location.conf")
        limits=source("infra/nginx/two-vm-public-requests.http.conf")
        static=source("infra/nginx/public-static.conf")
        self.assertIn("location = /v1/requests {",public)
        self.assertIn("limit_except POST",public)
        self.assertIn("proxy_ssl_verify on;",public)
        self.assertIn("proxy_ssl_certificate ",public)
        self.assertIn("proxy_ssl_trusted_certificate ",public)
        self.assertIn("proxy_set_header X-Museum-Client-IP $remote_addr;",public)
        self.assertIn('proxy_set_header Cookie "";',public)
        self.assertIn('proxy_set_header Authorization "";',public)
        self.assertIn("access_log off;",public)
        self.assertIn("proxy_pass https://10.20.30.10:9443;",public)
        self.assertEqual(len(re.findall(r"^\s*proxy_pass ",public,re.M)),1)
        self.assertNotIn("fastcgi_pass",public)
        self.assertNotIn("location / {",public)
        self.assertNotIn("proxy_pass",static)
        self.assertNotIn("fastcgi_pass",static)
        self.assertIn("limit_req_zone $binary_remote_addr",limits)

    def test_private_ingress_mtls_and_no_public_internal_pull(self):
        conf=source("infra/nginx/two-vm-private-ingress.conf")
        self.assertIn("listen 10.20.30.10:9443 ssl;",conf)
        self.assertIn("listen 127.0.0.1:8443 ssl;",conf)
        self.assertEqual(conf.count("ssl_verify_client on;"),2)
        self.assertIn("allow 10.20.30.20;",conf)
        self.assertIn("deny all;",conf)
        first, second=conf.split("server {")[1:]
        self.assertIn("location = /v1/requests",first)
        self.assertNotIn("/internal/pull",first)
        self.assertIn("location = /internal/pull",second)
        self.assertIn("location = /internal/ack",second)
        self.assertNotIn("location = /v1/requests",second)
        self.assertIn("fastcgi_param MUSEUM_CLIENT_IP $http_x_museum_client_ip;",first)
        self.assertNotIn("proxy_pass",conf)
        self.assertIn("unix:/run/musbread-ingress/ingress.sock",conf)

    def test_ingress_has_separate_sandbox_and_file_access(self):
        unit=source("infra/systemd/musbread-request-ingress-fpm.service")
        pool=source("infra/php-fpm/two-vm-request-ingress-pool.conf")
        self.assertIn("User=musbread-ingress",unit)
        self.assertIn("PrivateNetwork=true",unit)
        self.assertIn("RestrictAddressFamilies=AF_UNIX",unit)
        self.assertIn("ProtectSystem=strict",unit)
        self.assertIn("InaccessiblePaths=-/srv/musbread/cms",unit)
        self.assertIn("StateDirectory=musbread-requests",unit)
        self.assertIn("SupplementaryGroups=musbread-ingress-socket",unit)
        self.assertNotIn("SupplementaryGroups=www-data",unit)
        self.assertIn("listen.group = musbread-ingress-socket",pool)
        self.assertIn("clear_env = no",pool)
        self.assertIn("open_basedir",pool)
        self.assertIn("listen = /run/musbread-ingress/ingress.sock",pool)
        receiver=source("services/request-ingress/public/index.php")
        self.assertIn("cfg('MUSEUM_TRUSTED_PROXY')==='1'",receiver)
        self.assertIn("$_SERVER['MUSEUM_CLIENT_IP']",receiver)
        self.assertNotIn("$_SERVER['HTTP_X_MUSEUM_CLIENT_IP']",receiver)

    def test_spoofed_client_ip_header_cannot_bypass_trusted_fastcgi_guard(self):
        with tempfile.TemporaryDirectory(prefix="musbread-2vm-test-") as tmp:
            db=Path(tmp)/"queue.sqlite"
            pub=subprocess.check_output(["php","-r",
                "echo base64_encode(sodium_crypto_box_publickey(sodium_crypto_box_keypair()));"],
                text=True).strip()
            env=os.environ.copy()
            env.update(MUSEUM_INGRESS_DB=str(db),
                MUSEUM_INGRESS_PUBLIC_KEY=pub, MUSEUM_TRUSTED_PROXY="1",
                MUSEUM_ALLOWED_ORIGIN="https://musbread.ru",
                MUSEUM_RATE_SECRET="test-secret-only-"+"x"*50,
                MUSEUM_CONSENT_VERSION="test-v1")
            with socket.socket() as listener:
                listener.bind(("127.0.0.1",0))
                port=listener.getsockname()[1]
            url=f"http://127.0.0.1:{port}"
            proc=subprocess.Popen(["php","-S",f"127.0.0.1:{port}",
                "-t",str(ROOT/"services/request-ingress/public"),
                str(ROOT/"services/request-ingress/public/index.php")],
                env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                for _ in range(70):
                    try:
                        with urlopen(url+"/health",timeout=.5) as resp:
                            if resp.status==200: break
                    except Exception:
                        time.sleep(.05)
                else:
                    self.fail("synthetic PHP ingress did not start")
                payload=json.dumps({"kind":"feedback","name":"Иван",
                    "email":"synthetic@example.org","message":"Синтетика",
                    "consent":"test-v1"}).encode()
                request=Request(url+"/v1/requests",payload,method="POST",
                    headers={"Content-Type":"application/json",
                             "Origin":"https://musbread.ru",
                             "X-Museum-Client-IP":"198.51.100.1"})
                with self.assertRaises(HTTPError) as ctx:
                    urlopen(request,timeout=5)
                self.assertEqual(ctx.exception.code,503)
                ctx.exception.close()
                with sqlite3.connect(db) as conn:
                    self.assertEqual(conn.execute("SELECT COUNT(*) FROM inbox").fetchone()[0],0)
            finally:
                proc.terminate()
                proc.wait(timeout=5)


if __name__=="__main__":
    unittest.main()
