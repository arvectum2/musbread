#!/usr/bin/env bash
# Docker-only syntax test: synthetic certs, no network, no customer infrastructure.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
 -subj "/CN=ingress-private.example.invalid" \
 -keyout "$tmp/tls.key" -out "$tmp/tls.crt" >/dev/null 2>&1
for name in ingress-private ingress-internal public-proxy-client; do
 cp "$tmp/tls.crt" "$tmp/$name.crt"
 cp "$tmp/tls.key" "$tmp/$name.key"
done
cp "$tmp/tls.crt" "$tmp/internal-ca.crt"
mkdir -p "$tmp/cfg"
cp "$root/infra/nginx/two-vm-public-requests."*.conf "$tmp/cfg/"
sed -e "s/10\.20\.30\.10/127.0.0.1/g" -e "s/10\.20\.30\.20/127.0.0.1/g" \
 "$root/infra/nginx/two-vm-private-ingress.conf" > "$tmp/cfg/two-vm-private-ingress.conf"
cat > "$tmp/nginx.conf" <<'NGINX'
events {}
http {
    include /etc/nginx/mime.types;
    include /cfg/two-vm-public-requests.http.conf;
    server {
        listen 127.0.0.1:18080 ssl;
        server_name musbread.ru;
        ssl_certificate /etc/musbread/tls/ingress-private.crt;
        ssl_certificate_key /etc/musbread/tls/ingress-private.key;
        include /cfg/two-vm-public-requests.location.conf;
        location / { return 200 "synthetic-static"; }
    }
    include /cfg/two-vm-private-ingress.conf;
}
NGINX
docker run --rm --network none --entrypoint nginx \
 -v "$tmp/cfg:/cfg:ro" \
 -v "$tmp:/etc/musbread/tls:ro" \
 -v "$tmp/nginx.conf:/tmp/nginx.conf:ro" \
 nginx:stable-alpine -t -c /tmp/nginx.conf
