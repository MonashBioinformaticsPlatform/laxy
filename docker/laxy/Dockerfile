FROM python:3.6

ARG GIT_COMMIT=unspecified
LABEL git_commit=$GIT_COMMIT
ENV LAXY_VERSION=$GIT_COMMIT
ENV PYTHONUNBUFFERED 1

RUN mkdir /app
WORKDIR /app
ADD . /app/

RUN pip3 install -U pip && \
    pip3 install -U -r requirements.txt

RUN echo "LAXY_VERSION=$LAXY_VERSION" >>/etc/environment
