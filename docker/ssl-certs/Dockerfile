FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_BREAK_SYSTEM_PACKAGES=1

RUN apt-get update && \
    apt-get install --yes --no-install-recommends cron anacron openssl ca-certificates && \
    apt-get purge --yes exim4 exim4-base exim4-config exim4-daemon-light || true && \
    apt-get autoremove --yes && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# This is required for anacron to run. Also remove cron jobs we don't really need
RUN echo exit 0 > /usr/sbin/policy-rc.d && \
    rm -f /etc/cron.daily/apt-compat /etc/cron.daily/dpkg

RUN pip3 install --no-cache-dir -U pip setuptools wheel && \
    pip3 install --no-cache-dir certbot
ADD update-ssl-cert.sh /etc/cron.daily/update-ssl-cert.sh
RUN chmod +x /etc/cron.daily/update-ssl-cert.sh

# - Run the cron daemon (which calls anacron periodically)
# - Run pending anacron jobs immediately
# - If the key doesn't exist, try to get one immediately
# - Tail the log
CMD cron && anacron -n && ([ -f /certs/key.pem ] || /etc/cron.daily/update-ssl-cert.sh) && touch /var/log/ssl-certs-cron.log && tail -f /var/log/ssl-certs-cron.log
