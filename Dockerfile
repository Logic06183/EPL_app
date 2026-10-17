# FPL AI Pro API — Cloud Run image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/srv \
    PORT=8080 \
    ENVIRONMENT=production

WORKDIR /srv

COPY requirements_production.txt .
RUN pip install -r requirements_production.txt

COPY app/ ./app/

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8080

# Cloud Run ignores HEALTHCHECK; this is for docker / compose. /ping has no dependencies.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8080\")}/ping', timeout=4)"

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
