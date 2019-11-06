FROM python@sha256:f20a9bfddd87c238c3d2316b4179222f219090cbb25d5b6975070d4dd4b75004
# FROM python:3.6

ARG GIT_COMMIT=""
LABEL git_commit=$GIT_COMMIT
ENV LAXY_VERSION=$GIT_COMMIT
ENV PYTHONUNBUFFERED 1

RUN mkdir -p /app
WORKDIR /app
RUN groupadd -r --gid 999 laxy && \
    useradd -r --uid 999 --gid laxy -d /app -s /sbin/nologin -c "Laxy docker image user" laxy

ADD . /app/
RUN chown -R laxy:laxy /app

RUN pip3 install -U pip==19.2.2 && \
    pip3 install -U -r requirements.txt

# Temporary workaround for paramiko new OpenSSH key format (PR https://github.com/paramiko/paramiko/pull/1343)
# Alternative workaround - generate PEM format keys like:
#   ssh-keygen -t rsa -b 4096 -f ~/.ssh/my-compute-key -m PEM
RUN PARAMIKO_REPLACE=1 pip install --force https://github.com/ploxiln/paramiko-ng/archive/2.7.2.tar.gz#egg=paramiko

RUN echo "LAXY_VERSION=$LAXY_VERSION" >>/etc/environment
