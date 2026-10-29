#!/usr/bin/env bash
# Dedicated PHP-FPM pool/master syntax only; disposable container, no network.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
docker run --rm --network none --entrypoint sh \
 -v "$root/infra/php-fpm:/etc/musbread:ro" \
 php:8.4-fpm-alpine -ec '
    addgroup -S musbread-ingress
    addgroup -S musbread-ingress-socket
    adduser -S -D -G musbread-ingress musbread-ingress
    mkdir -p /run/musbread-ingress
    php-fpm -t --fpm-config /etc/musbread/two-vm-request-ingress-fpm.conf
 '
