#!/bin/sh
# LOCAL-ONLY: CMS -> Next.js static build -> versioned read-only release.
# This does not transfer data to the protected infrastructure of the museum.
set -eu

root="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$root"
if [ "${APP_ENV:-}" = production ] || { [ -f apps/cms/.env ] && grep -Eq '^APP_ENV=production([[:space:]]|$)' apps/cms/.env; }; then
  echo "Refusing demo publisher on APP_ENV=production" >&2
  exit 1
fi

mkdir -p deploy
lock="$root/deploy/.demo-publish-lock"
if ! mkdir "$lock" 2>/dev/null; then
  echo "Another demo publish appears to be running" >&2
  exit 1
fi
trap 'rmdir "$lock" 2>/dev/null || true' EXIT HUP INT TERM

if [ -x /opt/homebrew/opt/php@8.4/bin/php ]; then
  php_binary=/opt/homebrew/opt/php@8.4/bin/php
else
  php_binary="$(command -v php)"
fi

echo "[1/5] Export approved CMS content (private)"
(cd apps/cms && "$php_binary" artisan museum:export --preflight-strict)
echo "[2/5] Build static HTML"
(cd apps/web && NEXT_TELEMETRY_DISABLED=1 npm run build)
echo "[3/5] Generate strict, build-specific CSP for a future approved Nginx deployment"
python3 scripts/build_csp.py apps/web/out --output deploy/local/csp.generated.conf
echo "[4/5] Validate release and atomically switch current"
python3 scripts/release_site.py deploy
echo "[5/5] Verify all released checksums"
python3 scripts/release_site.py verify
