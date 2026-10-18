"""Release must stay NO-GO until source URLs become indexable originals."""
import csv,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_museum_seo_migration_cutover import audit
class SEOReleaseCutoverAuditTests(unittest.TestCase):
    def test_technical_audit_catches_legacy_meta_refresh_and_wrong_canonical_without_claiming_google_data(self):
        summary=audit()
        self.assertEqual(summary['release_decision'],'NO_GO')
        self.assertEqual(summary['original_old_page_routes'],518)
        self.assertEqual(summary['alias_meta_refresh_pages'],70)
        self.assertEqual(summary['source_old_details_pointing_at_anchors'],0)
        self.assertEqual(summary['new_target_missing_explicit_canonical'],0)
        self.assertEqual(summary['original_titles_not_in_new_title_or_h1'],0)
        self.assertEqual(summary['unintended_meta_refresh_pages'],0)
        self.assertEqual(summary['verified_original_drupal_redirects_pending_actual_nginx'],70)
        self.assertGreaterEqual(summary['uncovered_source_crosslink_paths'],2)
        self.assertEqual(summary['source_news'],280)
        self.assertEqual(summary['source_first_native_200_pages'],448)
        self.assertEqual(summary['source_first_native_news'],280)
        self.assertEqual(summary['source_first_native_exhibitions'],76)
        self.assertEqual(summary['original_photo_urls'],269)
        self.assertEqual(summary['photo_assets_missing'],0)
        self.assertEqual(summary['original_documents'],59)
        self.assertEqual(summary['document_files_missing_or_changed'],0)
        self.assertEqual(summary['nginx_rules_prepared_not_activated'],822)
        self.assertEqual(summary['old_website_broken_documents'],1)
        self.assertEqual(summary['old_website_unavailable_drupal_nodes'],1)
        self.assertTrue(summary['preview_robots_all_blocked'])
        self.assertEqual(summary['preview_sitemap_url_count'],0)
        self.assertEqual(summary['search_console_metrics'],'NOT_AVAILABLE')
    def test_full_legacy_url_matrix_has_one_entry_per_actual_source_path_and_no_unapproved_index_claims(self):
        with (ROOT/'docs/seo/URL_MIGRATION_MATRIX_20261018.csv').open(encoding='utf-8-sig') as file:
            rows=list(csv.DictReader(file,delimiter=';'))
        self.assertEqual(len(rows),518)
        self.assertEqual(len({row['legacy_path'] for row in rows}),518)
        self.assertTrue(all(row['legacy_url'].startswith('https://muzei-xleb.ru/') for row in rows))
        self.assertEqual(sum(row['seo_compatibility']=='NO_GO' for row in rows),70)
        self.assertEqual(sum(row['prototype_current_old_path_status']=='200_HTML' for row in rows),448)
        self.assertTrue(all(row['ownership_approval']=='NOT_APPROVED' for row in rows))
        self.assertEqual(sum(row['original_classification']=='original-news-article' for row in rows),280)
        self.assertTrue(all('full-source-html-200' in row['specific_finding'] or 'meta-refresh' in row['specific_finding'] for row in rows))
        self.assertTrue((ROOT/'docs/seo/CP_SEO_01_FIRST_POST_MIGRATION_AUDIT_20261018.md').is_file())
if __name__=='__main__':unittest.main()
