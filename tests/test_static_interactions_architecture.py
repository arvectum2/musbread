"""Static export and disabled intake architecture gates; no network or PII."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/architecture/visitor-interactions.v1.json"


class VisitorArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_public_is_static_and_read_only(self):
        public = self.data["public"]
        self.assertEqual(public["server"], "nginx-static-only")
        self.assertFalse(public["accepts_post"])
        self.assertFalse(public["stores_personal_data"])
        self.assertFalse(public["can_contact_cms_or_db"])
        config = (ROOT / "apps/web/next.config.ts").read_text(encoding="utf-8")
        self.assertIn('output: "export"', config)
        self.assertEqual(list((ROOT / "apps/web/src/app").rglob("route.ts")), [])

    def test_search_has_no_live_cms_dependency(self):
        self.assertEqual(self.data["search"]["index"], "published-snapshot-build-time")
        self.assertFalse(self.data["search"]["cms_queries_at_runtime"])

    def test_live_intake_is_not_secretly_enabled(self):
        req = self.data["requests"]
        self.assertEqual(req["current_delivery"], "mailto-draft")
        self.assertFalse(req["live_enabled"])
        source = (ROOT / "apps/web/src/components/MuseumVisitorInquiryForm.tsx").read_text(encoding="utf-8")
        self.assertIn("museumInquiryEmailDraft", source)
        self.assertIn("NEXT_PUBLIC_MUSEUM_REQUESTS_ENABLED", source)
        self.assertIn("if(!enabled)", source)
        self.assertIn("const response=await fetch(endpoint", source)
        self.assertIn("consentVersion.length>0", source)
        for forbidden in ["sendBeacon(", "localStorage", "sessionStorage"]:
            self.assertNotIn(forbidden, source)
        self.assertIn("disabled={!hydrated||pending}", source)

    def test_segmented_ingress_does_not_reach_cms(self):
        ingress = self.data["requests"]["ingress"]
        worker = self.data["requests"]["closed_worker"]
        self.assertEqual(ingress["path"], "/v1/requests")
        self.assertTrue(ingress["isolated_from_static_host"])
        self.assertFalse(ingress["has_cms_or_database_route"])
        self.assertFalse(ingress["has_cms_secrets"])
        self.assertTrue(ingress["no_extra_virtual_machine"])
        self.assertTrue(ingress["proxy_exception_requires_customer_approval"])
        self.assertTrue(ingress["durable_encrypted_queue"])
        self.assertFalse(ingress["plaintext_persistent_storage"])
        self.assertTrue(worker["initiates_private_mtls_pull"])
        self.assertFalse(worker["public_inbound_access"])
        self.assertFalse(worker["transfer_via_internet"])
        self.assertTrue(worker["idempotent_import"])
        self.assertTrue(worker["ack_after_durable_import"])

    def test_request_limits_and_failure_contract(self):
        req = self.data["requests"]
        self.assertEqual(req["kinds"], ["feedback", "excursion"])
        self.assertEqual(req["fields"]["name_max"], 100)
        self.assertEqual(req["fields"]["message_max"], 1200)
        self.assertEqual((req["fields"]["group_min"], req["fields"]["group_max"]), (1, 100))
        self.assertTrue(req["fields"]["personal_data_notice_approved_required"])
        self.assertFalse(req["fields"]["extra_fields"])
        self.assertLessEqual(req["ingress"]["max_payload_bytes"], 8192)
        self.assertFalse(req["ingress"]["attachments"])
        self.assertEqual(req["http"]["accepted"], 202)
        self.assertFalse(req["http"]["accepted_is_booking_confirmation"])
        self.assertEqual((req["http"]["limited"], req["http"]["unavailable"]), (429, 503))
        self.assertGreaterEqual(len(req["activation_requires"]), 5)

    def test_disabled_analytics_matches_source(self):
        self.assertFalse(self.data["third_party"]["analytics_enabled"])
        source = (ROOT / "apps/web/src/integrations/public.ts").read_text(encoding="utf-8")
        for flag in ["analyticsEnabled: false", "feedbackEnabled: false", "bookingEnabled: false"]:
            self.assertIn(flag, source)


if __name__ == "__main__":
    unittest.main()
