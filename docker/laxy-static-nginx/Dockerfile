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

# TODO: We could add a templated nginx.conf via
# ADD /app/docker/laxy-static/nginx/nginx.conf /tmp/nginx.conf
# RUN envsubst '${LAXY_FRONTEND_DOMAIN} ${LAXY_API_DOMAIN}' </tmp/nginx.conf >/etc/nginx/nginx.conf && \
#     rm /tmp/nginx.conf

COPY --from=frontend_build /app/laxy_frontend/dist/ /usr/share/nginx/html/

# We've already run collectstatic in during the laxy container build - grab the
# files from there, put them in the nginx container
COPY --from=laxy:latest /usr/share/nginx/html/backend_static /usr/share/nginx/html/backend_static

# RUN chmod -R a+r /usr/share/nginx/html

CMD ["nginx", "-g", "daemon off;"]
