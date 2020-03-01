FROM alpine:3.11.3

RUN apk upgrade && apk add --no-cache acme-client openssl
ADD update-ssl-cert.sh /etc/periodic/daily/update-ssl-cert.sh
RUN chmod +x /etc/periodic/daily/update-ssl-cert.sh

# Better to not do this and leave it up to the cron job, in case
# the container gets restarted many times in quick succession and exceeds
# the Let's Encrypt API rate limits
# CMD ["/etc/periodic/daily/update-ssl-cert.sh"]

# Run cron in the foreground
CMD ["crond", "-l2", "-f"]
