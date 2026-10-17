"""TZ-094: periodic security monitoring must not mutate dependencies."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DependencyReviewPolicyTests(unittest.TestCase):
    def test_weekly_readonly_jobs_cover_both_lockfiles(self):
        script = (ROOT / ".github/workflows/dependency-review.yml").read_text()
        self.assertIn("schedule:", script)
        self.assertIn("cron: '21 5 * * 1'", script)
        self.assertIn("workflow_dispatch:", script)
        self.assertIn("permissions:\n  contents: read", script)
        self.assertIn("npm audit --omit=dev --audit-level=high", script)
        self.assertIn("composer audit --locked --no-interaction", script)
        self.assertIn("npm ci --ignore-scripts --no-audit", script)
        self.assertNotIn("npm update", script)
        self.assertNotIn("composer update", script)
        self.assertNotIn("git push", script)

    def test_existing_ci_still_checks_both_ecosystems(self):
        script = (ROOT / ".github/workflows/web-ci.yml").read_text()
        self.assertIn("npm audit --omit=dev --audit-level=high", script)
        self.assertIn("composer audit --locked --no-interaction", script)
        self.assertTrue((ROOT / "apps/web/package-lock.json").exists())
        self.assertTrue((ROOT / "apps/cms/composer.lock").exists())


if __name__ == "__main__":
    unittest.main()
