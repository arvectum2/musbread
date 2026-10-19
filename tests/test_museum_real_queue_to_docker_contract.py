"""Pre-contract guards for true Laravel database worker -> Next -> Docker QA.

The complete integration suite is an explicit opt-in ~20s script on Mac mini.
These static tests run quickly as part of the existing all-museum Python suite.
"""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]

class RealQueuedLaravelStaticDockerContract(unittest.TestCase):
 def setUp(self):
  self.script=(ROOT/'scripts/qa_real_laravel_queue_to_static.py').read_text()
  self.docker=(ROOT/'scripts/verify_museum_two_contour_docker.py').read_text()
  self.job=(ROOT/'apps/cms/app/Jobs/PublishMuseumSnapshot.php').read_text()

 def test_real_laravel_database_queue_command_and_worker_are_not_mocks(self):
  self.assertIn("'QUEUE_CONNECTION':'database'",self.script)
  self.assertIn("'CACHE_STORE':'database'",self.script)
  self.assertIn("'museum:queue-export'",self.script)
  self.assertIn("'queue:work','database'",self.script)
  self.assertIn('actual_worker_processed',self.script)
  self.assertIn("result['runs'][0]['status']!='succeeded'",self.script)
  self.assertIn("result['failed_jobs']",self.script)

 def test_queued_snapshot_is_private_and_editorial_drafts_are_excluded(self):
  self.assertIn("'MUSEUM_QUEUED_EXPORT_STAGING_DIR':str(stage)",self.script)
  self.assertIn("'qa-real-queue-draft-hidden' in slugs",self.script)
  self.assertIn('web_developer_fixture_unchanged',self.script)
  self.assertIn("if before!=hashlib.sha256((WEB/'src/data/published.json').read_bytes()).hexdigest()",self.script)
  self.assertIn('draft_static_route_absent',self.script)
  self.assertIn('private queued export staging directory',self.job)
  self.assertIn('Queued publication stage cannot be inside public',self.job)

 def test_real_next_compilation_is_isolated_from_source_build_and_live_museum(self):
  self.assertIn("tempfile.TemporaryDirectory(prefix='queue-next-docker-'",self.script)
  self.assertIn("shutil.copytree(WEB,target",self.script)
  self.assertIn("meta['scripts'].pop('postbuild',None)",self.script)
  self.assertIn("'npm','run','build'",self.script)
  self.assertIn("out/news/qa-real-queue-draft-hidden/index.html'",self.script)
  self.assertIn("'noindex'",self.script)
  self.assertNotIn('https://zakupki.gov.ru',self.script)

 def test_real_worker_static_article_is_served_by_readonly_public_nginx_after_sha(self):
  self.assertIn("network_acceptance(source_output=target/'out',required_news=",self.script)
  self.assertIn("def test(source_output:Path|None=None,required_news:str|None=None):",self.docker)
  self.assertIn("src=source_output if source_output is not None else ROOT/'apps/web/out'",self.docker)
  self.assertIn('queue_built_news_visible_by_HTTP',self.docker)
  self.assertIn("'public_release_mount_read_only_Docker_named_volume':True",self.docker)
  self.assertIn('atomic_symlink_rollback_HTTP_restored_original',self.docker)

 def test_private_staging_is_opt_in_backwards_compatible_and_tested(self):
  config=(ROOT/'apps/cms/config/museum.php').read_text()
  self.assertIn("'queued_export_staging_dir' => env('MUSEUM_QUEUED_EXPORT_STAGING_DIR')",config)
  self.assertIn("if ($privateStage !== null && $privateStage !== '')",self.job)
  self.assertIn("$parameters['--document-output-dir']",self.job)
  self.assertIn("$this->outputPath !== null",self.job)
  php=(ROOT/'apps/cms/tests/Feature/MuseumQueuedPrivateStageTest.php').read_text()
  self.assertIn('test_queued_staging_refuses_real_public_webroot_even_if_existing',php)
  self.assertIn('test_real_worker_exports_content_only_to_private_staging',php)

if __name__=='__main__':unittest.main()
