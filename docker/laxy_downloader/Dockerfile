FROM python:3.12.16-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1

RUN apt-get update && apt-get install -y --no-install-recommends git libmagic1 aria2 procps ca-certificates && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the application directory
COPY ./laxy_downloader ./laxy_downloader

WORKDIR /app/laxy_downloader

# pip < 26.2.2 vendors a CA bundle that still trusts the compromised eMudhra
# intermediates, in addition to whatever certifi the app installs.
RUN pip install --no-cache-dir -U "pip>=26.2.2" && \
    pip install --no-cache-dir .

CMD ["laxydl"]
