"""Smoke contracts for the real protected editorial approval -> HTTP SLA QA."""
import unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]

class RealEditorialApprovalToHTTPContract(unittest.TestCase):
 def setUp(self):
  self.runner=(R/'scripts/qa_real_approval_to_public_http.py').read_text()
  self.php=(R/'apps/cms/tests/Feature/MuseumRealApprovalToQueuedExportTest.php').read_text()
 def test_admin_routes_capture_revisions_and_time_before_real_worker(self):
  for token in ('museum.entries.approve-and-queue','museum.events.approve-and-queue',
                'MuseumApprovalRevision::forSubject','approved_at','publication_run_id',
                "Artisan::call('queue:work'", "'connection' => 'database'",'DB::table(\'jobs\')'):
   self.assertIn(token,self.php)
 def test_approval_snapshot_is_verifiably_private_and_drafts_excluded(self):
  for token in ('MUSBREAD_APPROVAL_QA_OUTPUT_DIR','snapshot-manifest.json',
                'qa-unapproved-draft-hidden','MUSBREAD_APPROVAL_QA_OUTPUT_DIR',
                "assertSame('succeeded'",'getTimestamp()','snapshot_sha256'):
   self.assertIn(token,self.php)
 def test_real_web_build_and_docker_public_http_measured_from_saved_approval_clock(self):
  for token in ('tempfile.TemporaryDirectory','scripts[\'scripts\'].pop(\'postbuild\',None)',
                'NEXT_TELEMETRY_DISABLED', 'approval_to_public_HTTP_seconds',
                'real_museum_network_SLA_proven','verify_delivery(source_output=out',
                'real_admin_HTTP_POST','full_QA_wall_seconds'):
   self.assertIn(token,self.runner)
 def test_does_not_proclaim_real_museum_customer_network_sla(self):
  self.assertIn("'real_museum_network_SLA_proven':False",self.runner)
  self.assertIn('site_and_DNS_untouched',self.runner)
  self.assertNotIn('https://muzei-xleb.ru/',self.runner)

if __name__=='__main__':unittest.main()
