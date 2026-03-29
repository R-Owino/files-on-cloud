# Build stage
FROM python:3.11-alpine AS builder

# Update package index and install build dependencies
RUN apk update && apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev

# Install Python dependencies
WORKDIR /app
COPY api/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# Test stage
FROM python:3.11-alpine AS test

# Install runtime dependencies
RUN apk add --no-cache libffi openssl && \
    addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application and test files
COPY --chown=appuser:appuser api/v1/app.py api/v1/cognito.py api/v1/config.py api/v1/__init__.py /app/v1/
COPY --chown=appuser:appuser api/v1/routes/ /app/v1/routes/
COPY --chown=appuser:appuser api/v1/static/ /app/v1/static/
COPY --chown=appuser:appuser api/v1/templates/ /app/v1/templates/
COPY --chown=appuser:appuser api/tests /app/tests

USER appuser
WORKDIR /app
ENV PYTHONPATH=/app \
    PATH="/usr/local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    AWS_SECRET_NAME=filesoncloud-app-secrets \
    AWS_REGION=us-west-2

# Testing command
CMD ["python", "-m", "pytest", "tests/", "-v"]

# Production stage
FROM python:3.11-alpine AS production

# Install runtime dependencies and create user
RUN apk add --no-cache libffi openssl && \
    addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application files
COPY --chown=appuser:appuser api/v1/app.py api/v1/cognito.py api/v1/config.py api/v1/__init__.py /app/v1/
COPY --chown=appuser:appuser api/v1/routes/ /app/v1/routes/
COPY --chown=appuser:appuser api/v1/static/ /app/v1/static/
COPY --chown=appuser:appuser api/v1/templates/ /app/v1/templates/

USER appuser
WORKDIR /app/v1
ENV PYTHONPATH=/app \
    PATH="/usr/local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    AWS_SECRET_NAME=filesoncloud-app-secrets \
    AWS_REGION=us-west-2

CMD ["gunicorn", "-w", "4", "-k", "gthread", "-b", "0.0.0.0:5000", "v1.app:app"]
