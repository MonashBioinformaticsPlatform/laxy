#!/bin/bash
# /etc/cron.daily/update-ssl-cert.sh
# Must be: chmod +x /etc/cron.daily/update-ssl-cert.sh

ACME_SSL_DOMAINS="${ACME_SSL_DOMAINS-laxy.io api.laxy.io dev.laxy.io dev-api.laxy.io}"

EMAIL_OPT="--register-unsafely-without-email"
if [[ ! -z ${LAXY_ADMIN_EMAIL} ]]; then
    EMAIL_OPT="--email ${LAXY_ADMIN_EMAIL}"
fi

mkdir -p /usr/share/nginx/html/.well-known/acme-challenge
rm -rf /var/log/ssl-certs-cron.log
touch /var/log/ssl-certs-cron.log

DOMAIN_ARGS=$(echo ' '${ACME_SSL_DOMAINS} | sed "s/ / -d /g")
PRIMARY_DOMAIN=$(echo ${ACME_SSL_DOMAINS} | awk '{print $1}')

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
certbot certonly \
    --config-dir /certs/letsencrypt \
    --work-dir /certs/letsencrypt-work \
    --logs-dir /certs/letsencrypt-logs \
    --webroot -w /usr/share/nginx/html \
    ${DOMAIN_ARGS} \
    ${EMAIL_OPT} \
    --agree-tos \
    --non-interactive \
    --cert-name ${PRIMARY_DOMAIN} \
    --keep-until-expiring \
    >>/var/log/ssl-certs-cron.log 2>&1 \
&& cp /certs/letsencrypt/live/${PRIMARY_DOMAIN}/privkey.pem /certs/key.pem \
&& cp /certs/letsencrypt/live/${PRIMARY_DOMAIN}/cert.pem /certs/cert.pem \
&& cp /certs/letsencrypt/live/${PRIMARY_DOMAIN}/chain.pem /certs/chain.pem \
&& cp /certs/letsencrypt/live/${PRIMARY_DOMAIN}/fullchain.pem /certs/fullchain.pem \
|| generate_selfsigned

# If there is no key and fullchain nginx won't start. This might happen if the ACME client fails for some reason.
# In that case, so create a temporary self-signed one (generate_selfsigned)
