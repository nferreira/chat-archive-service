# 001 — Dependency Injector, Makefile & Docker DB Initialisation

## Overview

Three related improvements applied in sequence:

1. **Dependency Injector** — Replace manual wiring of repos/use-cases with `dependency-injector` container.
2. **Makefile** — Add a sectioned Makefile covering build, app, test, lint, docker, compose, and database targets.
3. **Docker DB initialisation** — Make Postgres credentials configurable via `.env` and run an init script on first container start.

---

## Files Created

### `chat_archive/container.py`

Central DI container + FastAPI dependency functions.

```python
class Container(DeclarativeContainer):
    wiring_config = WiringConfiguration(modules=[
        "chat_archive.infrastructure.web.routes_v1",
    ])
    config = Configuration()

    engine = Singleton(create_async_engine, config.database_url, echo=False)
    session_factory = Singleton(async_sessionmaker, engine, expire_on_commit=False)
```

FastAPI dependency functions that bridge the container into request-scoped deps:

- `get_session(factory=Depends(Provide[Container.session_factory]))` — async generator yielding `AsyncSession`
- `get_message_repository(session=Depends(get_session))` — returns `PostgresMessageRepository`
- `get_store_message_use_case(repo=Depends(get_message_repository))` — returns `StoreMessageUseCase`
- `get_messages_by_user_use_case(repo=...)` — returns `GetMessagesByUserUseCase`
- `get_delete_user_use_case(repo=...)` — returns `DeleteUserUseCase`

### `chat_archive/application/app.py`

The `App` class moved here from `chat_archive/main.py`.

- `__init__` creates `Container`, sets `config.database_url` from `DATABASE_URL` env var, calls `container.wire()`, logs masked DB URL.
- `container` property exposes the container.
- Lifespan uses `self._container.engine()` for dispose.

### `Makefile`

Sectioned Makefile with the following target groups:

| Section          | Targets                                                  |
|------------------|----------------------------------------------------------|
| Help             | `help`                                                   |
| Build            | `install`, `sync`, `lock`, `build`, `clean`              |
| App              | `run`, `dev`, `migrate`, `migrate-down`, `revision`      |
| Test             | `test`, `test-v`, `test-cov`, `test-cov-html`            |
| Lint / Format    | `lint`, `format`, `check`                                |
| Docker           | `docker-build`, `docker-run`, `docker-stop`, `docker-clean` |
| Docker Compose   | `up`, `build-up`, `down`, `restart`, `logs`, `ps`        |
| Database         | `db-up`, `db-down`, `db-reset`, `db-logs`, `shell-postgres` |

The Makefile includes `.env` (without exporting) so that `APP_DB_USER` / `APP_DB_NAME` are available for `shell-postgres`. `DATABASE_URL` is intentionally **not** exported — local commands use the `engine.py` default (`localhost`), and Docker Compose constructs it inline.

### `docker/postgres/init-db.sh`

Entrypoint init script mounted into `/docker-entrypoint-initdb.d/`. Runs once on first container start (empty data directory). Uses `APP_DB_USER`, `APP_DB_PASSWORD`, `APP_DB_NAME`, `APP_DB_SCHEMA` env vars to:

1. Create the application database (if not exists).
2. Create a least-privilege application role (if not exists).
3. Create a non-public schema (if `APP_DB_SCHEMA != public`).
4. Grant `CONNECT`, `USAGE`, `CREATE` on schema, and default privileges for tables/sequences.

### `.env`

Credentials for local development. **Not committed** (added to `.gitignore`).

```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
APP_DB_USER=chat_app
APP_DB_PASSWORD=chat_app_secret
APP_DB_NAME=chat_archive
APP_DB_SCHEMA=public
```

Does **not** contain `DATABASE_URL` — that is constructed by Docker Compose from the individual vars, or falls back to the `engine.py` default for local runs.

### `.env.example`

Checked-in template with placeholder passwords.

---

## Files Modified

### `pyproject.toml`

- Added `"dependency-injector>=4.42"` to `[project] dependencies`.
- Changed wheel exclude from `test_*.py` to `*_test.py`.

### `chat_archive/main.py`

Reduced to a two-line entry point:

```python
from chat_archive.application.app import App
app = App()
```

### `chat_archive/infrastructure/db/engine.py`

Stripped down to two items:

- `DATABASE_URL` constant (read from env, fallback to `localhost`).
- `_mask_password()` helper.

Removed: `engine`, `async_session_factory`, `get_session` (all moved to container).

### `chat_archive/infrastructure/web/routes_v1.py`

- Imports dependency functions from `chat_archive.container`.
- Routes inject via `Depends(get_store_message_use_case)`, `Depends(get_session)`, etc.
- No more manual `PostgresMessageRepository(session)` or `UseCase(repo)` in handlers.
- `get_messages` route (multi-dispatch: day vs period) injects `get_message_repository` and creates the needed use case inline.

### `chat_archive/infrastructure/web/routes_v1_test.py` (renamed from `test_routes_v1.py`)

- Imports `get_session` from `chat_archive.container` instead of `engine`.
- Override via `app.fastapi.dependency_overrides[get_session]`.

### `chat_archive/application/use_cases_test.py` (renamed from `test_use_cases.py`)

- **No code changes** — unit tests mock the repo directly, no container involved.
- Renamed to follow `{file}_test.py` convention.

### `chat_archive/infrastructure/migrations/alembic.ini`

- Removed hardcoded `sqlalchemy.url`. URL is now resolved at runtime from `DATABASE_URL` env var via `env.py`.

### `chat_archive/infrastructure/migrations/env.py`

- Imports `DATABASE_URL` and `_mask_password` from `engine.py` (single source of truth).
- `get_url()` raises `RuntimeError` if no URL is available.
- Logs the masked database URL before running migrations and a completion message after.

### `docker-compose.yml`

- Both services use `env_file: .env`.
- `db` service mounts `docker/postgres/init-db.sh` into `/docker-entrypoint-initdb.d/`.
- `app` service constructs `DATABASE_URL` inline: `postgresql+psycopg://${APP_DB_USER}:${APP_DB_PASSWORD}@db:5432/${APP_DB_NAME}`.
- Healthcheck uses configured user/database.

### `.gitignore`

- Added `.env`.

---

## Verification

```bash
uv sync                  # dependency-injector installs
make migrate             # migrations run against localhost, logs masked URL
make test                # all 21 tests pass
make help                # shows all Makefile targets
```
