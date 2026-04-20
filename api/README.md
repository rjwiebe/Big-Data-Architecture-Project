# RTD Denver API

This directory contains the FastAPI application for determining the nearest 10 transit stations and feeding them with real-time transit data.

## Getting Started

1. Copy the example environment file:

   ```bash
   cp api/.env.example api/.env
   ```

2. Set up a Python Virtual Environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install Requirements:
   ```bash
   pip install -r api/requirements.txt
   ```

   For backend tests, install the dev requirements instead:

   ```bash
   pip install -r api/requirements-dev.txt
   ```

4. Configure environment variables in `api/.env`:
   ```bash
   POSTGRES_DSN=postgresql://user:password@host:5432/database
   REDIS_URL=redis://host:6379/0
   ALLOWED_ORIGINS=https://your-mobile-preview-host.example.com
   PORT=8080
   ```

4. Configure environment variables in `api/.env`:
   ```bash
   POSTGRES_DSN=postgresql://user:password@host:5432/database
   REDIS_URL=redis://host:6379/0
   REDIS_TTL=900
   ALLOWED_ORIGINS=https://your-mobile-preview-host.example.com
   PORT=8080
   

   `POSTGRES_DSN` is required. `REDIS_URL` and `ALLOWED_ORIGINS` are optional.

5. Run the dev server from the repository root:
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```

The Swagger docs will be available at `http://localhost:8000/docs`.

## Cloud Run

Build the API container from the repository root:

```bash
docker build -f api/Dockerfile -t rtd-api .
```

Or use the helper deploy script:

```bash
PROJECT_ID=your-project \
REGION=us-central1 \
SERVICE_NAME=rtd-api \
POSTGRES_DSN_SECRET=postgres-dsn \
./scripts/deploy-api-cloud-run.sh
```

The container starts with:

```bash
uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

For GCP deployment:

- Run FastAPI on Cloud Run
- Provide `POSTGRES_DSN` through Secret Manager or deploy-time env vars
- Point `REDIS_URL` at Memorystore only if realtime cache lookups are enabled
- Keep static GTFS tables preloaded in Cloud SQL before exposing the API

## Contract Tests

Run the API contract tests with:

```bash
python -m unittest discover api/tests
```
