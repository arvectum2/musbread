#!/bin/sh
# Source TZ 2.2.3.5 & 2.2.3.8.3: true Chromium-GOST on private Mac mini.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
BROWSER="$ROOT/.local_archive/browser_compat_20261019/apps/Chromium-Gost.app/Contents/MacOS/Chromium-Gost"
[ -x "$BROWSER" ] || { echo 'Install official macOS-arm64 Chromium-GOST into private archive first' >&2;exit 2; }
ROOT="$ROOT" python3 - <<'PY'
import json,sys,os
from pathlib import Path
sys.path.insert(0,'scripts')
from build_museum_legacy_page_aliases import build_map
p=Path('.local_archive/browser_compat_20261019/official_html_paths.json')
p.parent.mkdir(parents=True,exist_ok=True)
corpus=sorted(k for k,v in build_map().items() if v['why']!='source-verified-drupal-node')
assert len(corpus)==467,len(corpus)
p.write_text(json.dumps(corpus,ensure_ascii=False)+'\n')
PY
NAME="musbread-gost-qa-$$"
cleanup(){ docker stop "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT INT TERM
docker run -d --rm --name "$NAME" -p 127.0.0.1:18088:8080 \
 --mount "type=bind,source=$ROOT/deploy/nginx/museum_local_loopback.conf,target=/etc/nginx/nginx.conf,readonly" \
 --mount "type=bind,source=$ROOT/deploy/nginx,target=/etc/nginx/musbread,readonly" \
 --mount "type=bind,source=$ROOT/apps/web/out,target=/srv/musbread,readonly" \
 nginx:stable-alpine >/dev/null
for i in 1 2 3 4 5 6 7 8 9 10; do
 if curl --silent --fail --head http://127.0.0.1:18088/robots.txt | grep -qi 'X-Musbread-Local-Test: isolated'; then break; fi
 sleep 1
done
curl -sSfI http://127.0.0.1:18088/robots.txt | grep -qi 'X-Musbread-Local-Test: isolated'
node scripts/browser-tests/check_chromium_gost.cjs
