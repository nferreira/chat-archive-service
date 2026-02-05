from __future__ import annotations

import os

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Enable SQL query logging with LOG_LEVEL=DEBUG or SQL_ECHO=true
SQL_ECHO = os.environ.get("SQL_ECHO", "").lower() in ("1", "true", "yes")

from chat_archive.application.delete_user.use_case import DeleteUserUseCase
from chat_archive.application.get_messages_by_user.use_case import GetMessagesByUserUseCase
from chat_archive.application.store_message.use_case import StoreMessageUseCase
from chat_archive.infrastructure.db.repositories.message_repository_pg import PostgresMessageRepository


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "chat_archive.infrastructure.web.routes_v1",
        ],
    )

    config = providers.Configuration()

    engine = providers.Singleton(create_async_engine, config.database_url, echo=SQL_ECHO)
    session_factory = providers.Singleton(
        async_sessionmaker, engine, expire_on_commit=False
    )


@inject
async def get_session(
    factory: async_sessionmaker = Depends(Provide[Container.session_factory]),
) -> AsyncSession:  # type: ignore[misc]
    async with factory() as session:
        yield session


async def get_message_repository(
    session: AsyncSession = Depends(get_session),
) -> PostgresMessageRepository:
    return PostgresMessageRepository(session)


async def get_store_message_use_case(
    repo: PostgresMessageRepository = Depends(get_message_repository),
) -> StoreMessageUseCase:
    return StoreMessageUseCase(repo)


async def get_messages_by_user_use_case(
    repo: PostgresMessageRepository = Depends(get_message_repository),
) -> GetMessagesByUserUseCase:
    return GetMessagesByUserUseCase(repo)


async def get_delete_user_use_case(
    repo: PostgresMessageRepository = Depends(get_message_repository),
) -> DeleteUserUseCase:
    return DeleteUserUseCase(repo)
