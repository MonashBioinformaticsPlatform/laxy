FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends git libmagic1 aria2 procps && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the application directory
COPY ./laxy_downloader ./laxy_downloader

WORKDIR /app/laxy_downloader

# Install the application and its dependencies
RUN pip install .

ENTRYPOINT ["laxydl"]
