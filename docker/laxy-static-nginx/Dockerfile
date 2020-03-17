#
# This images builds the web frontend and packages it with nginx.
# The nginx config
# It also grabs the Django admin static files from a pre-build laxy:latest image.
#

FROM node:12 AS frontend_build
ARG LAXY_STATIC_ROOT=/usr/share/nginx/html/backend_static
ARG GIT_COMMIT=unspecified
ARG LAXY_FRONTEND_URL=http://localhost:8002
ARG LAXY_FRONTEND_API_URL=http://localhost:8001
ARG LAXY_FRONTEND_GOOGLE_OAUTH_CLIENT_ID=""
ARG LAXY_ENV=prod

ENV LAXY_VERSION=$GIT_COMMIT
ENV LAXY_FRONTEND_URL=$LAXY_FRONTEND_URL
ENV LAXY_FRONTEND_API_URL=$LAXY_FRONTEND_API_URL
ENV LAXY_FRONTEND_GOOGLE_OAUTH_CLIENT_ID=$LAXY_FRONTEND_GOOGLE_OAUTH_CLIENT_ID
ENV LAXY_ENV=$LAXY_ENV

ADD laxy_frontend /app/laxy_frontend
WORKDIR /app/laxy_frontend

RUN rm -rf node_modules && \
    rm -rf dist && \
    touch ../.env && \
    npm install && \
    npm run build:$LAXY_ENV

FROM nginx:1.15-alpine
LABEL git_commit=$GIT_COMMIT

ADD docker/laxy-static-nginx/nginx.conf.template /etc/nginx/nginx.conf.template

COPY --from=frontend_build /app/laxy_frontend/dist/ /usr/share/nginx/html/

# We've already run collectstatic in during the laxy (django) container build - grab the
# files from there, put them in the nginx container.
# (The alternative would be to include a build stage above where we install all the Python
#  dependencies etc just to run ./manager.py collectstatic - this would
#  be duplicating code from docker/laxy/Dockerfile, so seems like a bad idea)
COPY --from=laxy:latest /usr/share/nginx/html/backend_static /usr/share/nginx/html/backend_static

# Reload nginx daily to ensure we get updated ssl certificates
RUN echo -e '#!/bin/sh\n/usr/sbin/nginx -s reload' >/etc/periodic/daily/nginx-reload-config && \
    chmod +x /etc/periodic/daily/nginx-reload-config

RUN echo "LAXY_VERSION=$LAXY_VERSION" >>/etc/environment

# We extract the FQDN for the frontend and backend and substitute these values into the nginx.conf template
# on startup
CMD export LAXY_FRONTEND_HOST=`echo $LAXY_FRONTEND_URL | cut -f 2 -d ':' | sed 's/\/\///g'` && \
    export LAXY_API_HOST=`echo $LAXY_FRONTEND_API_URL | cut -f 2 -d ':' | sed 's/\/\///g'` && \
    (envsubst '${LAXY_FRONTEND_HOST} ${LAXY_API_HOST}' </etc/nginx/nginx.conf.template >/etc/nginx/nginx.conf || true) && \
    nginx -g 'daemon off;'
