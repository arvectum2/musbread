"""Local publication must never run against a declared production CMS."""
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PublicationGuardTests(unittest.TestCase):
    def test_demo_pipeline_refuses_production_app_env_before_touching_files(self):
        env = dict(os.environ, APP_ENV="production")
        result = subprocess.run(
            ["sh", "scripts/demo_publish.sh"], cwd=ROOT, env=env,
            capture_output=True, text=True, timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Refusing demo publisher on APP_ENV=production", result.stderr)
        self.assertNotIn("[1/5]", result.stdout)

    def test_demo_pipeline_mandates_strict_preflight(self):
        source = (ROOT / "scripts/demo_publish.sh").read_text()
        self.assertIn('artisan museum:export --preflight-strict', source)
        self.assertIn('python3 scripts/release_site.py verify', source)
        self.assertIn('mkdir "$lock"', source)
        self.assertNotIn("npm run dev", source)


if __name__ == "__main__":
    unittest.main()
