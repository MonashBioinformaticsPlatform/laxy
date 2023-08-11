FROM python@sha256:a489206b7ab876ad948f577c498ed79af77b8f0f1f6f92a43af94304c529f793
# FROM python:3.8

RUN apt update && \
    apt install --yes cron anacron && \
    apt purge --yes exim4 exim4-base exim4-config exim4-daemon-light && \
    apt autoremove --yes && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
# This is required for anacron to run. Also remove cron jobs we don't really need
RUN echo exit 0 > /usr/sbin/policy-rc.d && \
    rm -f /etc/cron.daily/apt-compat /etc/cron.daily/dpkg

RUN cd / && \
    git clone https://github.com/zenhack/simp_le.git && \
    cd simp_le && \
    pip install -e .
ADD update-ssl-cert.sh /etc/cron.daily/update-ssl-cert.sh
RUN chmod +x /etc/cron.daily/update-ssl-cert.sh

# - Run the cron daemon (which calls anacron periodically)
# - Run pending anacron jobs immediately
# - If the key doesn't exist, try to get one immediately
# - Tail the log
CMD cron && anacron -n && ([ -f /certs/key.pem ] || /etc/cron.daily/update-ssl-cert.sh) && touch /var/log/ssl-certs-cron.log && tail -f /var/log/ssl-certs-cron.log
