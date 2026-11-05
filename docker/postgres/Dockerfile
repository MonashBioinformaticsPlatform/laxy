FROM postgres:15-alpine

# ca-certificates-bundle before 20261020-r0 still trusts the compromised
# eMudhra intermediates. Upgrade at build time so a stale postgres tag is not enough.
RUN apk add --no-cache --upgrade ca-certificates
