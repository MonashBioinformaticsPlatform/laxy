FROM nginx:1.15-alpine

ARG GIT_COMMIT=unspecified
LABEL git_commit=$GIT_COMMIT
ENV LAXY_VERSION=$GIT_COMMIT

# Copy the result of:
#   cd laxy_frontend; npm run build:prod
ADD ./laxy_frontend/dist/ /usr/share/nginx/html/

# Copy the result of:
#   LAXY_STATIC_ROOT=./.ignore/tmp/laxy_backend_static/ ./manage.py collectstatic
ADD ./.ignore/tmp/laxy_backend_static/ /usr/share/nginx/html/backend_static
