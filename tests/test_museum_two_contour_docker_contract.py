"""Architectural guards for the opt-in CP-ARCH-01 isolated Docker acceptance.

Normal Python CI runs structural tests only. To re-run the integration test,
use scripts/verify_museum_two_contour_docker.py on the authorized Mac mini.
"""
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]

class MuseumPrivatePublicDockerContract(unittest.TestCase):
 def setUp(self):
  self.src=(ROOT/'scripts/verify_museum_two_contour_docker.py').read_text(encoding='utf-8')
 def test_private_network_and_cms_never_export_host_port(self):
  self.assertIn("'network','create','--internal',private_network",self.src)
  self.assertIn("'php:8.4-cli'",self.src)
  self.assertIn("'--network',private_network",self.src)
  self.assertIn("'NetworkSettings']['Ports'].get('8081/tcp')",self.src)
  self.assertIn("'public_to_private_direct_access_denied':True",self.src)
  self.assertIn("'private_to_public_direct_access_denied':True",self.src)
 def test_release_volume_is_linux_local_and_readonly_from_public(self):
  self.assertIn("run('volume','create',volume)",self.src)
  self.assertIn("f'type=volume,source={volume},target=/published'",self.src)
  self.assertIn("f'type=volume,source={volume},target=/srv/public,readonly'",self.src)
  self.assertIn("'mv','-Tf'",self.src)
  self.assertIn("'public_release_mount_read_only_Docker_named_volume':True",self.src)
 def test_transfer_manifest_is_outside_transport_and_negative_attacks_are_checked(self):
  self.assertIn("make_manifest(sender,trusted)",self.src)
  self.assertIn("verify_manifest(staged,trusted)",self.src)
  self.assertIn("sha(incoming.read_bytes())!=sha(archive.read_bytes())",self.src)
  self.assertIn("'modified_static_html_rejected':True",self.src)
  self.assertIn("'injected_php_file_rejected':True",self.src)
  self.assertIn("'tampered_second_release_blocked_before_switch':True",self.src)
  self.assertIn("'atomic_symlink_rollback_HTTP_restored_original':True",self.src)
 def test_cleanup_of_both_networks_volume_and_all_containers_guaranteed(self):
  self.assertIn("'127.0.0.1:{PORT}:8080'",self.src)
  self.assertIn(' finally:',self.src)
  self.assertIn("for name in containers:run('rm','-f',name,check=False",self.src)
  self.assertIn("for name in networks:run('network','rm',name,check=False",self.src)
  self.assertIn("run('volume','rm',volume,check=False",self.src)
  self.assertIn('shutil.rmtree(home,ignore_errors=True)',self.src)
 def test_scope_is_not_misrepresented_as_actual_museum_production_or_full_cms(self):
  self.assertIn('NOT actual Laravel CMS publisher',self.src)
  self.assertIn('5 REAL Next.js static output files',self.src)
  self.assertIn('prod_network_and_SSL_tested',self.src)
  self.assertIn('synthetic_second_artifact_NOT_editorial_CMS_approval',self.src)

if __name__=='__main__':unittest.main()
