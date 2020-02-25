#!/bin/bash
# /etc/cron.daily/update-ssl-cert.sh
# Must be: chmod +x /etc/cron.daily/update-ssl-cert.sh

ACME_SSL_DOMAINS="${ACME_SSL_DOMAINS-laxy.io api.laxy.io dev.laxy.io dev-api.laxy.io}"

EMAIL_OPT=""
if [[ ! -z ${LAXY_ADMIN_EMAIL} ]]; then
    EMAIL_OPT="--email ${LAXY_ADMIN_EMAIL}"
fi

mkdir -p /usr/share/nginx/html/.well-known/acme-challenge
rm -rf /var/log/ssl-certs-cron.log
touch /var/log/ssl-certs-cron.log

DOMAIN_ARGS=$(echo ' '${ACME_SSL_DOMAINS} | sed "s/ / -d /g")

function generate_selfsigned() {
    if [[ ! -f /certs/key.pem ]] && [[ ! -f /certs/fullchain.pem ]]; then
      openssl req -x509 -newkey rsa:4096 \
                  -keyout /certs/key.pem  \
                  -out /certs/fullchain.pem \
                  -days 1 -nodes -subj '/CN=localhost' \
                   >>/var/log/ssl-certs-cron.log 2>&1
    fi
}

cd /certs/
/usr/local/bin/simp_le \
    -f account_key.json \
    -f account_reg.json \
    -f key.pem \
    -f cert.pem \
    -f fullchain.pem \
    -f chain.pem \
    ${DOMAIN_ARGS} \
    ${EMAIL_ADDRESS} \
    --default_root /usr/share/nginx/html \
    >>/var/log/ssl-certs-cron.log 2>&1 || generate_selfsigned

# If there is no key and fullchain nginx won't start. This might happen if the ACME client fails for some reason.
# In that case, so create a temporary self-signed one (generate_selfsigned)
