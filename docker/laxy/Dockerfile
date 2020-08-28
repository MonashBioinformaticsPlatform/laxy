FROM python@sha256:f20a9bfddd87c238c3d2316b4179222f219090cbb25d5b6975070d4dd4b75004
# FROM python:3.6

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

# Install node/npm and build the frontend
#RUN curl -sL https://deb.nodesource.com/setup_12.x | bash - && apt-get install -y nodejs
#RUN cd laxy_frontend && \
#    rm -rf node_modules && \
#    rm -rf dist && \
#    touch ../.env && \
#    npm install && \
#    npm run build:prod

# RUN mkdir -p /usr/share/nginx/html && cp -r /app/laxy_frontend/dist/* /usr/share/nginx/html/

# RUN chown -R laxy:laxy /app

RUN export PIP_DISABLE_PIP_VERSION_CHECK=1 && \
    pip3 install -U pip==19.2.2 && \
    pip3 install -U -r requirements.txt

# We collect Django admin staticfiles, to be shared with the nginx container
# (via volume or COPY --from laxy:latest at container build time)
RUN mkdir -p $LAXY_STATIC_ROOT && \
    LAXY_SECRET_KEY=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1) \
    python3 manage.py collectstatic --no-input

RUN echo "LAXY_VERSION=$LAXY_VERSION" >>/etc/environment
