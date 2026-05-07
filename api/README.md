# The API

The Flask application that serves the FilesOnCloud web interface. It handles user authentication, file operations, and communicates with AWS services directly (S3, Cognito) or through the API Gateway/Lambda layer (file metadata, delete).

## Directory structure

```
api/
├── Dockerfile          # Multi-stage build: builder → test → production
├── pyproject.toml      # Dependencies managed with uv
├── uv.lock             # Pinned lockfile
├── tests/              # pytest test suite (moto for AWS mocking)
│   ├── conftest.py     # Shared fixtures: mock Redis, mock AWS config, Flask test client
│   └── test_*.py       # One test file per route module
└── v1/
    ├── app.py          # Flask application factory, session config, blueprint registration
    ├── config.py       # Configuration loader: env vars → Secrets Manager → Parameter Store
    ├── cognito.py      # Cognito IdP wrappers: register, confirm, login, delete_user
    ├── routes/
    │   ├── upload.py           # Multipart upload: initialize, chunk presigned URLs, complete
    │   ├── download.py         # CloudFront signed URL generation + proxy
    │   ├── delete.py           # File deletion via API Gateway (Cognito-authorized)
    │   ├── file_metadata.py    # Fetch recent files via API Gateway
    │   ├── search_file.py      # File search via API Gateway
    │   ├── check_file.py       # Duplicate filename detection
    │   ├── login.py            # Login form → Cognito InitiateAuth → session
    │   ├── register.py         # Registration form → Cognito SignUp
    │   ├── confirm.py          # Email verification code submission
    │   ├── resend_code.py      # Resend confirmation code
    │   ├── logout.py           # Session clearance
    │   ├── delete_account.py   # Account deletion: DynamoDB first, then Cognito
    │   ├── main.py             # Dashboard route
    │   ├── landing.py          # Public landing page
    │   ├── health.py           # /health, /health/liveness, /health/readiness
    │   └── private_key.pem     # CloudFront signing key (not committed — see setup below)
    ├── static/
    │   ├── css/                # Per-page stylesheets
    │   └── js/                 # fileUpload.js, fileDisplay.js, fileActions.js, etc.
    └── templates/              # Jinja2 HTML templates
```

## Configuration

`config.py` loads values in priority order:

1. **Environment variables** - highest priority; used for `REDIS_HOST` in local dev
2. **AWS Secrets Manager** - `SECRET_KEY`, `REDIS_PASSWORD`
3. **AWS Parameter Store** - everything else: Cognito IDs, API Gateway URLs, S3 bucket, CloudFront domain/key IDs, DynamoDB table names

In production (ECS), the `ENVIRONMENT=prod` env var tells the app to use `localhost` for Redis (sidecar container in the same task) and to read all config from Secrets Manager / Parameter Store.

In local development (`ENVIRONMENT=local`), Redis is reached at `REDIS_HOST=redis` (the Docker Compose service name).

## Development setup

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
# Create and activate a virtual environment
uv venv
source .venv/bin/activate 

# Install all dependencies including dev tools
uv sync
```

### CloudFront signing key

The download route signs URLs with a private RSA key. Generate the key pair once and place the private key in `api/v1/routes/`:

```bash
openssl genrsa -out api/v1/routes/private_key.pem 2048
openssl rsa -pubout -in api/v1/routes/private_key.pem -out infra/modules/cloudfront/public_key.pem
```

The private key is listed in `.gitignore` and must never be committed. It is injected into the CI pipeline via the `PRIVATE_KEY` GitHub Actions secret.

## Running tests

Tests mock all AWS services with `moto` and mock Redis via `conftest.py`, no live infrastructure required.

```bash
# From the project root
uv run --project api pytest api/tests/ -v
```

Or with an activated virtualenv:

```bash
pytest api/tests/ -v
```

## Docker build

The Dockerfile has three targets:

| Target | Purpose |
|---|---|
| `builder` | Installs production dependencies into `/app/.venv` using uv |
| `test` | Installs all dependencies (including dev), runs pytest |
| `production` | Copies the venv from builder, runs Gunicorn |

Build and test locally:

```bash
# Run tests
docker build --target test -t filesOnCloud-test -f api/Dockerfile .
docker run --rm filesOnCloud-test

# Build production image
docker build --target production -t filesOnCloud -f api/Dockerfile .
```

## Key design decisions

**Session storage** - Flask-Session uses Redis in production and SimpleCache in tests. Session lifetime is 30 minutes. The session cookie is HttpOnly, Secure (prod), and SameSite=Lax.

**SigV4 presigned URLs** - The S3 client is explicitly configured with `signature_version="s3v4"` for all presigned URL generation. SigV2 presigned URLs do not work with STS temporary credentials (which ECS tasks use) because they require the security token as a request header that the browser does not know to send.

**Account deletion order** - `delete_user` deletes the DynamoDB userdata record first, then the Cognito user. This ensures the account is only removed from Cognito once the database side has succeeded, if the DynamoDB delete fails, the user can still log in and retry.

**File categorization** - Uploaded files are automatically placed into S3 folders (`text-files/`, `image-files/`, `video-files/`, `audio-files/`, `other-files/`) based on file extension.
