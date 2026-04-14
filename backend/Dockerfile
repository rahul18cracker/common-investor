FROM python:3.14-alpine AS builder

RUN apk add --no-cache build-base

WORKDIR /build
COPY requirements.lock /build/requirements.lock
RUN pip install --no-cache-dir --prefix=/install -r requirements.lock

# --- Production stage ---
FROM python:3.14-alpine

# Patch OS-level CVEs (openssl, zlib) and Python vendored CVEs (jaraco.context, wheel)
RUN apk upgrade --no-cache && \
    pip install --no-cache-dir --upgrade setuptools wheel

# Create non-root user
RUN addgroup -g 1000 appuser && \
    adduser -u 1000 -G appuser -s /bin/sh -D appuser

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY scripts /app/scripts

# Own the app directory
RUN chown -R appuser:appuser /app

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

USER appuser
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v1/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
