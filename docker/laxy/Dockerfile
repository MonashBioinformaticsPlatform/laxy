FROM python:3.6

ARG GIT_COMMIT=unspecified
LABEL git_commit=$GIT_COMMIT
ENV LAXY_VERSION=$GIT_COMMIT
ENV PYTHONUNBUFFERED 1

RUN mkdir -p /app
WORKDIR /app
RUN groupadd -r --gid 999 laxy && \
    useradd -r --uid 999 --gid laxy -d /app -s /sbin/nologin -c "Laxy docker image user" laxy

ADD . /app/
RUN chown -R laxy:laxy /app

RUN pip3 install -U pip && \
    pip3 install -U -r requirements.txt

RUN echo "LAXY_VERSION=$LAXY_VERSION" >>/etc/environment
