import unittest
from scripts.qa_nginx_concurrent_load import check_local_url, percentile

class LocalLoadSafetyTests(unittest.TestCase):
    def test_literal_loopback_allowed(self):
        self.assertEqual(check_local_url("http://127.0.0.1:18118"), "http://127.0.0.1:18118")
    def test_no_external_host(self):
        for endpoint in ("https://muzei-xleb.ru", "http://localhost:18118",
                         "http://127.0.0.1:18118@evil.example", "http://127.0.0.2:18118",
                         "https://127.0.0.1:18118", "http://127.0.0.1:18118/other",
                         "http://127.0.0.1:18118?q=1"):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                check_local_url(endpoint)
    def test_nearest_rank(self):
        self.assertEqual(percentile([1, 2, 3, 4], .95), 4)
if __name__ == "__main__":
    unittest.main()
