# Docker

This project supports a fully containerized workflow using Docker and Docker Compose.
For local development instructions, see ../README.md.

## Services

`docker-compose.yml` defines two services:
- `db`: PostgreSQL 17 (Alpine)
- `app`: FastAPI app built from `Dockerfile`

Default ports:
- Postgres: `5432`
- API: `8000`

## Environment

Compose loads `.env` for database credentials and names:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `APP_DB_USER`, `APP_DB_PASSWORD`, `APP_DB_NAME`, `APP_DB_SCHEMA`

The app container receives `DATABASE_URL` internally:
`postgresql+psycopg://${APP_DB_USER}:${APP_DB_PASSWORD}@db:5432/${APP_DB_NAME}`

## Common Commands

Start all services:
```bash
make up
```

Stop all services:
```bash
make down
```

Rebuild and start:
```bash
make build-up
```

Run app + db in the foreground (builds first):
```bash
make docker-run
```

Tail logs:
```bash
make logs
```

List running containers:
```bash
make ps
```

## Database Helpers

Start only Postgres:
```bash
make db-up
```

Stop Postgres:
```bash
make db-down
```

Reset database volume:
```bash
make db-reset
```

Open `psql` inside the container:
```bash
make shell-postgres
```

## Health Checks

- App: `GET /health`
- DB: `pg_isready` in Compose

## Notes

- When using Compose, the database runs inside the `db` container, not on localhost.
- `make migrate` should be run after `make up` so the schema is created.
- If the app fails to start, check `.env` values and `make logs`.
