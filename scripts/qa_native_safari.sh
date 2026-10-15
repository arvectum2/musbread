#!/bin/sh
# Mac-only native Safari document/navigation smoke, without Docker.
# Requires a built static site. Existing Safari windows are left intact.
set -eu
root="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
if [ ! -f "$root/apps/web/out/index.html" ]; then
  echo "Build Next.js first: cd apps/web && npm run build" >&2
  exit 1
fi
if /usr/sbin/lsof -nP -iTCP:18779 -sTCP:LISTEN 2>/dev/null | grep -q .; then
  echo "Port 18779 is occupied. Refusing to interrupt another process." >&2
  exit 1
fi
python3 -m http.server 18779 --bind 127.0.0.1 --directory "$root/apps/web/out" \
    > /tmp/musbread-native-safari-server.log 2>&1 &
server=$!
trap 'kill "$server" 2>/dev/null || true; wait "$server" 2>/dev/null || true' EXIT HUP INT TERM
ready=0
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS -o /dev/null http://127.0.0.1:18779/; then ready=1; break; fi
  sleep .3
done
if [ "$ready" != 1 ]; then
  echo "Local Safari QA server failed to start" >&2
  exit 1
fi
/usr/bin/osascript "$root/scripts/qa_native_safari.applescript"
