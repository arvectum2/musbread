#!/usr/bin/env python3
"""Ephemeral localhost acceptance: queue persistence, sealed PII, auth and ack."""
import base64
import json
import os
import sqlite3
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:18279"


class IngressTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="musbread-ingress-")
        cls.db = str(Path(cls.tmp.name) / "queue.sqlite")
        pair = subprocess.check_output(["php", "-r",
            "echo base64_encode(sodium_crypto_box_publickey($p=sodium_crypto_box_keypair())).\"\\n\";"
            "echo base64_encode(sodium_crypto_box_secretkey($p));"]).decode().splitlines()
        cls.secret = pair[1]
        env = os.environ.copy()
        env.update(MUSEUM_INGRESS_DB=cls.db, MUSEUM_INGRESS_PUBLIC_KEY=pair[0],
            MUSEUM_ALLOWED_ORIGIN="https://musbread.ru",
            MUSEUM_RATE_SECRET="demo-test-key-only-aaaaaaaaaaaaaaaaaaaaaaaaaaaa", MUSEUM_CONSENT_VERSION="test-v1",
            MUSEUM_INTERNAL_TOKEN="X" * 64)
        cls.proc = subprocess.Popen(["php", "-S", "127.0.0.1:18279",
                                     "-t", str(ROOT / "public"),
                                     str(ROOT / "public/index.php")],
                                    env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                if cls.call("GET", "/health")[0] == 200:
                    cls.call("GET", "/internal/pull", headers={"Authorization": "Bearer " + "X"*64})
                    return
            except Exception:
                time.sleep(.05)
        raise RuntimeError("local test ingress never started")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=5)
        cls.tmp.cleanup()

    @classmethod
    def call(cls, method, path, data=None, headers=None):
        headers = headers or {}
        raw = json.dumps(data).encode("utf-8") if data is not None else None
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = Request(URL + path, raw, method=method, headers=headers)
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, response.read().decode("utf-8")
        except HTTPError as error:
            try:
                return error.code, error.read().decode("utf-8")
            finally:
                error.close()

    def setUp(self):
        with sqlite3.connect(self.db) as db:
            db.execute("DELETE FROM limits")
            db.execute("DELETE FROM receipts")
            db.execute("DELETE FROM inbox")

    def test_full_flow(self):
        h = {"Origin": "https://musbread.ru"}
        submission = {"client_id": "a"*32, "kind": "feedback", "name": "Тестовый посетитель",
                      "email": "visitor@example.org", "message": "Вопрос о часах работы",
                      "consent": "test-v1"}
        self.assertEqual(self.call("POST", "/v1/requests", submission, {"Origin": "https://wrong.ru"})[0], 403)
        self.assertEqual(self.call("POST", "/v1/requests", dict(submission, consent="wrong"), h)[0], 422)
        self.assertEqual(self.call("POST", "/v1/requests", dict(submission, extra="x"), h)[0], 422)
        self.assertEqual(self.call("GET", "/internal/pull")[0], 403)
        self.assertEqual(self.call("POST", "/internal/ack", {"ids": ["a"*32]})[0], 403)
        status, payload = self.call("POST", "/v1/requests", submission, h)
        self.assertEqual(status, 202, payload)
        request_id = json.loads(payload)["request_id"]
        db = sqlite3.connect(self.db)
        stored = db.execute("SELECT envelope FROM inbox WHERE id=?", (request_id,)).fetchone()[0]
        self.assertNotIn("Тестовый", stored)
        self.assertNotIn("visitor@example.org", stored)
        self.assertNotIn("Вопрос", stored)
        token = {"Authorization": "Bearer " + "X"*64}
        status, payload = self.call("GET", "/internal/pull", headers=token)
        self.assertEqual(status, 200, payload)
        items = json.loads(payload)["items"]
        self.assertEqual(len(items), 1)
        status, duplicate = self.call("POST", "/v1/requests", submission, h)
        self.assertEqual(status, 202)
        self.assertEqual(json.loads(duplicate)["request_id"], request_id)
        self.assertEqual(sqlite3.connect(self.db).execute("SELECT COUNT(*) FROM inbox").fetchone()[0], 1)
        self.assertEqual(self.call("POST", "/v1/requests", dict(submission, message="Modified"), h)[0], 409)
        self.assertEqual(items[0]["id"], request_id)
        envelope = items[0]["envelope"]
        # Cross-language/libsodium verification of real sealed box.
        decrypted = subprocess.check_output(["php", "-r",
            "$s=base64_decode($argv[1]);$secret=base64_decode($argv[2]);"
            "$key=sodium_crypto_box_keypair_from_secretkey_and_publickey("
            "$secret,sodium_crypto_box_publickey_from_secretkey($secret));"
            "$clear=sodium_crypto_box_seal_open($s,$key);"
            "if($clear===false)exit(1);echo $clear;", envelope, self.secret]).decode()
        self.assertEqual(json.loads(decrypted)["message"], submission["message"])
        status, _ = self.call("POST", "/internal/ack", {"ids": [request_id]}, token)
        self.assertEqual(status, 200)
        self.assertEqual(self.call("GET", "/internal/pull", headers=token)[1], '{"items":[]}')
        # idempotent acknowledgements after interrupted worker retries
        self.assertEqual(self.call("POST", "/internal/ack", {"ids": [request_id]}, token)[0], 200)
        db.close()

    def test_excursion_validation_and_limits(self):
        h = {"Origin": "https://musbread.ru"}
        data = {"kind": "excursion", "name": "Иван", "email": "visitor@example.org",
                "message": "Группа", "date": "2026-02-31", "group_size": 3, "consent": "test-v1"}
        self.assertEqual(self.call("POST", "/v1/requests", data, h)[0], 422)
        self.assertEqual(self.call("POST", "/v1/requests", dict(data, date="2026-11-06", group_size=101), h)[0], 422)
        self.assertEqual(self.call("POST", "/v1/requests", dict(data, date="2026-11-06"), h)[0], 202)
        self.assertEqual(self.call("POST", "/v1/requests", dict(data, date="2026-11-06", website="spam"), h)[0], 202)
        db = sqlite3.connect(self.db)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM inbox").fetchone()[0], 1)
        for _ in range(4):
            self.call("POST", "/v1/requests", dict(data, date="2026-11-06"), h)
        self.assertEqual(self.call("POST", "/v1/requests", dict(data, date="2026-11-06"), h)[0], 429)
        self.assertEqual(self.call("POST", "/v1/requests", dict(data, date="2026-11-06", message="X"*9000), h)[0], 413)
        db.close()


if __name__ == "__main__":
    unittest.main()
