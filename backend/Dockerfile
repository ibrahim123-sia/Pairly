# Pairly API.
#   docker build -t pairly-api ./backend
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app/backend

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN useradd --create-home --uid 10001 pairly \
    && mkdir -p /app/backend/data \
    && chown -R pairly:pairly /app

ENV APP_ENV=production \
    APP_DEBUG=false \
    DATA_DIR=/app/backend/data \
    PORT=5000

USER pairly
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"5000\")}/api/health', timeout=4)"

ENTRYPOINT ["sh", "/app/backend/docker-entrypoint.sh"]
