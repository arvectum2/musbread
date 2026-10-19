#!/bin/sh
# Isolated production-style HTTP acceptance of the private static museum copy.
# Uses only 127.0.0.1 and read-only source/asset mounts; NEVER touches DNS.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PORT=${MUSBREAD_NGINX_PORT:-18088}
case "$PORT" in ''|*[!0-9]*) echo 'Invalid loopback test port' >&2; exit 2;; esac
[ "$PORT" -ge 1024 ] && [ "$PORT" -le 65535 ] || { echo 'Loopback port must be 1024..65535' >&2; exit 2; }
NAME="musbread-nginx-local-test-$$"
IMAGE="nginx:stable-alpine"
cleanup(){ docker stop "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT INT TERM
[ -d "$ROOT/apps/web/out" ] || { echo 'Run npm run build:museum-deploy first' >&2; exit 2; }
[ -x "$ROOT/.venv/bin/python" ] || { echo 'Missing project private Python environment' >&2; exit 2; }
# Only pull a lightweight Nginx image into the local Docker cache as needed.
docker image inspect "$IMAGE" >/dev/null 2>&1 || docker pull "$IMAGE" >/dev/null
printf 'CP-SEO-06: Nginx syntax test (isolated container, no public ports)\n'
docker run --rm --name "$NAME-config" --entrypoint nginx \
  --mount "type=bind,source=$ROOT/deploy/nginx/museum_local_loopback.conf,target=/etc/nginx/nginx.conf,readonly" \
  --mount "type=bind,source=$ROOT/deploy/nginx,target=/etc/nginx/musbread,readonly" \
  --mount "type=bind,source=$ROOT/apps/web/out,target=/srv/musbread,readonly" \
  "$IMAGE" -t
printf 'CP-SEO-06: serve only on Mac mini localhost port %s\n' "$PORT"
docker run -d --rm --name "$NAME" -p "127.0.0.1:$PORT:8080" --entrypoint nginx \
  --mount "type=bind,source=$ROOT/deploy/nginx/museum_local_loopback.conf,target=/etc/nginx/nginx.conf,readonly" \
  --mount "type=bind,source=$ROOT/deploy/nginx,target=/etc/nginx/musbread,readonly" \
  --mount "type=bind,source=$ROOT/apps/web/out,target=/srv/musbread,readonly" \
  "$IMAGE" -g 'daemon off;' >/dev/null
ready=0
n=0
while [ "$n" -lt 15 ]; do
  if curl --silent --fail --max-time 2 -I "http://127.0.0.1:$PORT/robots.txt" | grep -qi 'X-Musbread-Local-Test: isolated'; then ready=1; break; fi
  n=$((n+1)); sleep 1
done
[ "$ready" -eq 1 ] || { echo 'Isolated Nginx did not start' >&2; exit 1; }
printf 'CP-TZ241: Nginx must gzip public HTML, leaving PDF originals unchanged.\n'
gzip_headers=$(curl --silent --show-error --max-time 15 --dump-header - \
  --output /dev/null --header "Accept-Encoding: gzip" "http://127.0.0.1:$PORT/news/")
printf '%s\n' "$gzip_headers" | grep -qi "^Content-Encoding: gzip" || {
  echo "Expected gzip news-index HTML on local Nginx" >&2; exit 1; }
gzip_size=$(curl --silent --show-error --max-time 15 \
  --header "Accept-Encoding: gzip" --output /dev/null \
  --write-out "%{size_download}" "http://127.0.0.1:$PORT/news/")
printf 'CP-TZ241: real Nginx gzip news transferred %s bytes\n' "$gzip_size"
MUSBREAD_NGINX_PORT="$PORT" "$ROOT/.venv/bin/python" "$ROOT/scripts/audit_museum_nginx_http_loopback.py"
MUSBREAD_NGINX_PORT="$PORT" "$ROOT/.venv/bin/python" "$ROOT/scripts/audit_museum_pdf_viewability_loopback.py"
printf 'CP-SEO-06: isolated Nginx success; container is auto-removed. Live museum unchanged.\n'
