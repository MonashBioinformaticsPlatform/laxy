FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PIP_BREAK_SYSTEM_PACKAGES=1
WORKDIR /app

COPY laxy_mcp/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY laxy_mcp/server.py /app/server.py

EXPOSE 8003
CMD ["python", "server.py"]
