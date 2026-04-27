FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements_production.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements_production.txt

COPY app/ ./app/

EXPOSE 8080

ENV PYTHONPATH=/app
ENV PORT=8080
ENV ENVIRONMENT=production

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
