#!/bin/sh
# /etc/periodic/daily/update-ssl-cert.sh
# Must be: chmod +x /etc/periodic/daily/update-ssl-cert.sh

ACME_SSL_DOMAINS="${ACME_SSL_DOMAINS-laxy.io api.laxy.io dev.laxy.io dev-api.laxy.io}"

# acme-client docs: https://kristaps.bsd.lv/acme-client/acme-client.1.html
# EXTRA_ARGS="-s -F" # -s = staging, -F = force renewal
EXTRA_ARGS="" # -s = staging, -F = force renewal
AGREEMENT_URL="https://letsencrypt.org/documents/LE-SA-v1.2-November-15-2017.pdf"

mkdir -p /usr/share/nginx/html/.well-known/acme-challenge

# If there is no key, nginx won't start, so create a temporary self-signed one. acme-client will replace it.
if [ ! -f /certs/domain.key ]; then
  openssl req -x509 -newkey rsa:4096 \
              -keyout /certs/domain.key \
              -out /certs/fullchain.pem \
              -days 1 -nodes -subj '/CN=localhost'
fi

/usr/bin/acme-client \
            -a $AGREEMENT_URL \
            -f /certs/account.key \
            -C /usr/share/nginx/html/.well-known/acme-challenge/ \
            -c /certs \
            -k /certs/domain.key \
            -Nnmev \
            $EXTRA_ARGS \
            $ACME_SSL_DOMAINS
