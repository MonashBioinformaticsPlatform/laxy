
FROM python:3.12

ARG LAXY_STATIC_ROOT=/usr/share/nginx/html/backend_static
ARG GIT_COMMIT=""
LABEL git_commit=$GIT_COMMIT
ENV LAXY_VERSION=$GIT_COMMIT
ENV PYTHONUNBUFFERED 1

RUN mkdir -p /app
WORKDIR /app

RUN groupadd -r --gid 999 laxy && \
    useradd -r --uid 999 --gid laxy -d /app -s /sbin/nologin -c "Laxy docker image user" laxy

ADD --chown=laxy:laxy . /app/

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
RUN pip3 install --no-cache-dir -U pip "setuptools>=75,<82" && \
    pip3 install --no-cache-dir -U -r requirements.txt

# We collect Django admin staticfiles, to be shared with the nginx container
# (via volume or COPY --from laxy:latest at container build time)
RUN mkdir -p $LAXY_STATIC_ROOT && \
    LAXY_SECRET_KEY=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1) \
    python3 manage.py collectstatic --no-input

RUN echo "LAXY_VERSION=$LAXY_VERSION" >>/etc/environment
