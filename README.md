# Chat Archive Service

FastAPI service for storing and querying chat messages. It provides message
ingest, user queries, date-range queries, and GDPR-style deletion.

## Requirements

- Python 3.11+
- `uv` (for dependency management)
- PostgreSQL 15+ (or use Docker Compose)
- Docker + Docker Compose (optional, recommended for quickstart)

## Quickstart (Docker Compose)

1. Create a `.env` file.
   Copy `.env.example` to `.env` and edit values if needed.
2. Start services with `make up` (or `docker compose up -d`).
3. Run migrations with `make migrate`.
4. Open the API docs at `http://localhost:8000/docs`.

OpenAPI and docs endpoints:
- `http://localhost:8000/openapi.json`
- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

Health check:
- `http://localhost:8000/health`

## Local Development (no Docker)

1. Install dependencies with `make install`.
2. Set your database URL.
   `export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/chat_archive`
   The app defaults to the URL above if `DATABASE_URL` is not set.
3. Run migrations with `make migrate`.
4. Start the API server with `make dev`.

## Configuration

Environment variables:
- `DATABASE_URL` (used by the app and migrations)

Docker Compose variables (from `.env`):
- `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `APP_DB_USER`, `APP_DB_PASSWORD`, `APP_DB_NAME`, `APP_DB_SCHEMA`

## Common Commands

Build and install:
- `make install` (installs dependencies with `uv`)
- `make build` (builds a wheel)

Run:
- `make dev` (auto-reload)
- `make run` (production-like)

Migrations:
- `make migrate`
- `make migrate-down`
- `make revision msg="describe change"`

Testing and linting:
- `make test`
- `make test-cov`
- `make lint`
- `make format`

Docker:
- `make docker-build`
- `make docker-run` (foreground)
- `make up` / `make down`

## Additional Docs

See `docs/README.md` for extended documentation:
- Docker details: `docs/docker.md`
- Deployment notes: `docs/deploy.md`
- OpenAPI/docs endpoints: `docs/openapi.md`

## API Overview

Base path: `/api/v1`

Endpoints:
- `POST /api/v1/messages` Store a message
- `GET /api/v1/messages` Query by day or period
- `GET /api/v1/users/{user_id}/messages` Query by user and date range
- `DELETE /api/v1/users/{user_id}` Delete user data
- `GET /health` Health check

Pagination:
- `page_size` (default 50, max 100)
- `page` (0-indexed)
- When there are no results, the API returns `204 No Content` with headers:
  `X-Total-Count`, `X-Page-Size`, `X-Page`

Request correlation headers:
- Optional: `X-Request-ID`, `X-Client-ID`
- Returned on every response for log correlation

## Example Requests

Store a message:
```bash
curl -X POST "http://localhost:8000/api/v1/messages" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"jdoe","name":"John Doe","question":"Hello?","answer":"Hi!"}'
```

Get messages by day:
```bash
curl "http://localhost:8000/api/v1/messages?day=2026-02-04&page_size=20&page=0"
```

Get messages by period:
```bash
curl "http://localhost:8000/api/v1/messages?start=2026-02-01&end=2026-02-05&page_size=50&page=0"
```

Get messages by user:
```bash
curl "http://localhost:8000/api/v1/users/jdoe/messages?start=2026-02-01&end=2026-02-05"
```

Delete a user:
```bash
curl -X DELETE "http://localhost:8000/api/v1/users/jdoe"
```

## Makefile API Shortcuts

The `Makefile` includes helper targets that wrap the API:
- `make store-message user_id=jdoe name='John Doe' question='Hello?' answer='Hi!'`
- `make get-messages-by-user user_id=jdoe start=2026-02-01 end=2026-02-05 page_size=10`
- `make get-messages-by-day day=2026-02-04 page_size=20 page=0`
- `make get-messages-by-period start=2026-02-01 end=2026-02-05 page_size=50 page=0`
- `make delete-user user_id=jdoe`

## Load Testing

Scripts in `scripts/load_test.py` can seed and stress test the API:
- `make load-seed count=10000`
- `make load-read concurrency=20 duration=60`
- `make load-write concurrency=10 duration=30`
- `make load-full seed_count=5000 concurrency=10 duration=30`
