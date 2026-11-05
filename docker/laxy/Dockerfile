# syntax=docker/dockerfile:1
FROM python:3.12.16

ARG LAXY_STATIC_ROOT=/usr/share/nginx/html/backend_static
# Consumed only after the dependency layers, so a new commit does not bust apt/pip cache.
ARG GIT_COMMIT=""

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache && \
    apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    update-ca-certificates

WORKDIR /app

# Manifest only. The tree is copied afterwards so source edits reuse this layer.
COPY requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip3 install -U "pip>=26.2.2" "setuptools>=75,<82" && \
    pip3 install -U -r requirements.txt

RUN groupadd -r --gid 999 laxy && \
    useradd -r --uid 999 --gid laxy -d /app -s /sbin/nologin -c "Laxy docker image user" laxy

ADD --chown=laxy:laxy . /app/

# We collect Django admin staticfiles, to be shared with the nginx container
# (via volume or COPY --from laxy:latest at container build time)
RUN mkdir -p $LAXY_STATIC_ROOT && \
    LAXY_SECRET_KEY=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1) \
    python3 manage.py collectstatic --no-input

LABEL git_commit=$GIT_COMMIT
ENV LAXY_VERSION=$GIT_COMMIT
RUN echo "LAXY_VERSION=$LAXY_VERSION" >>/etc/environment
