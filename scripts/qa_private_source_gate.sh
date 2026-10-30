#!/usr/bin/env bash
# Fail-closed gate for a trusted local machine WITH original EIS and museum archives.
# Never send original files, credentials, signed PDF, archive HTML, or full pages to GitHub.
set -euo pipefail
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != "--with-browser" ) ]]; then
  echo "Usage: $0 [--with-browser]" >&2
  exit 2
fi
WITH_BROWSER=${1:-}
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "PRIVATE_GATE_BLOCKED: reproducible virtual environment .venv/bin/python missing" >&2
  exit 2
fi
if [[ ! -d "$ROOT/.local_archive" ]]; then
  echo "PRIVATE_GATE_BLOCKED: authenticated original museum archive missing" >&2
  exit 2
fi
echo "PRIVATE_GATE: signed EIS contract, all 325 TZ atoms, and source line fingerprints"
python3 scripts/check_speckit_tz.py --verify-source
python3 scripts/audit_signed_contract.py --verify-source
echo "PRIVATE_GATE: 101 exact PDF/DOCX originals, 259 original photos, 27 archived news indexes and all local links"
"$PY" scripts/build_complete_museum_static_release.py --verify-only
echo "PRIVATE_GATE: complete unrestricted Python test suite, including source SHA proof"
"$PY" -m unittest discover -s tests
echo "PRIVATE_GATE: production PHP dependencies, and native Laravel regression"
(
  cd apps/cms
  composer audit --locked --no-interaction
  php artisan test --compact --no-ansi
)
if [[ "$WITH_BROWSER" == "--with-browser" ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "PRIVATE_GATE_BLOCKED: npm is required for strict source-backed browser E2E" >&2
    exit 2
  fi
  echo "PRIVATE_GATE: all real-browser E2E including CSP and complete WCAG census"
  ( cd apps/web && npm run test:e2e -- --workers=1 )
fi
echo "PRIVATE_MUSBREAD_ORIGINAL_GATE_PASS (not museum acceptance, no deployment)"
