# Build stage
FROM python:3.11-alpine AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev

WORKDIR /app
COPY api/pyproject.toml api/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

RUN apk del .build-deps

# Test stage
FROM python:3.11-alpine AS test

RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev && \
    addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY api/pyproject.toml api/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project && \
    apk del .build-deps

COPY --chown=appuser:appuser api/v1/app.py api/v1/cognito.py api/v1/config.py api/v1/__init__.py /app/v1/
COPY --chown=appuser:appuser api/v1/routes/ /app/v1/routes/
COPY --chown=appuser:appuser api/v1/static/ /app/v1/static/
COPY --chown=appuser:appuser api/v1/templates/ /app/v1/templates/
COPY --chown=appuser:appuser api/tests /app/tests

USER appuser
ENV PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    AWS_SECRET_NAME=filesoncloud-app-secrets \
    AWS_REGION=us-west-2

CMD ["python", "-m", "pytest", "tests/", "-v"]

# Production stage
FROM python:3.11-alpine AS production

RUN apk add --no-cache libffi openssl && \
    addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

COPY --from=builder /app/.venv /app/.venv

COPY --chown=appuser:appuser api/v1/app.py api/v1/cognito.py api/v1/config.py api/v1/__init__.py /app/v1/
COPY --chown=appuser:appuser api/v1/routes/ /app/v1/routes/
COPY --chown=appuser:appuser api/v1/static/ /app/v1/static/
COPY --chown=appuser:appuser api/v1/templates/ /app/v1/templates/

USER appuser
WORKDIR /app/v1
ENV PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    AWS_SECRET_NAME=filesoncloud-app-secrets \
    AWS_REGION=us-west-2

CMD ["gunicorn", "-w", "4", "-k", "gthread", "-b", "0.0.0.0:5000", "v1.app:app"]
