FROM python:3.9.4

RUN apt update && \
    apt install --yes cron anacron && \
    apt purge --yes exim4 exim4-base exim4-config exim4-daemon-light && \
    apt autoremove && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
# This is required for anacron to run. Also remove cron jobs we don't really need
RUN echo exit 0 > /usr/sbin/policy-rc.d && \
    rm -f /etc/cron.daily/apt-compat /etc/cron.daily/dpkg

RUN pip3 install -U simp-le-client==0.17.0
ADD update-ssl-cert.sh /etc/cron.daily/update-ssl-cert.sh
RUN chmod +x /etc/cron.daily/update-ssl-cert.sh

# - Run the cron daemon (which calls anacron periodically)
# - Run pending anacron jobs immediately
# - If the key doesn't exist, try to get one immediately
# - Tail the log
CMD cron && anacron -n && ([ -f /certs/key.pem ] || /etc/cron.daily/update-ssl-cert.sh) && touch /var/log/ssl-certs-cron.log && tail -f /var/log/ssl-certs-cron.log
