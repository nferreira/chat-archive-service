from __future__ import annotations

import asyncio
import logging
import os

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from chat_archive.infrastructure.db.engine import DATABASE_URL, _mask_password
from chat_archive.infrastructure.db.orm import Base

log = logging.getLogger("alembic.env")

target_metadata = Base.metadata


def get_url() -> str:
    url = os.environ.get("DATABASE_URL", DATABASE_URL)
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set and no default is available."
        )
    return url


def run_migrations_offline() -> None:
    url = get_url()
    log.info("Running migrations offline against %s", _mask_password(url))
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
    log.info("Offline migrations completed")


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    url = get_url()
    log.info("Running migrations against %s", _mask_password(url))
    connectable = create_async_engine(url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()
    log.info("Migrations completed")


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
