"""Integration tests for PostgresMessageRepository using SQLite."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from chat_archive.domain.models.message import Message
from chat_archive.infrastructure.db.orm import Base
from chat_archive.infrastructure.db.repositories.message_repository_pg import (
    PostgresMessageRepository,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///file::memory:?cache=shared"


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


def _make_message(**overrides) -> Message:
    defaults = dict(
        id=uuid.uuid4(),
        user_id="user-1",
        name="Alice",
        question="What is Python?",
        answer="A programming language.",
        created_at=datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return Message(**defaults)


class TestPostgresMessageRepositorySave:
    @pytest.mark.asyncio
    async def test_save_returns_message(self, test_session: AsyncSession):
        repo = PostgresMessageRepository(test_session)
        msg = _make_message()

        result = await repo.save(msg)

        assert result.id == msg.id
        assert result.user_id == msg.user_id

    @pytest.mark.asyncio
    async def test_save_persists_to_database(self, test_session: AsyncSession):
        repo = PostgresMessageRepository(test_session)
        msg = _make_message()

        await repo.save(msg)
        await test_session.commit()

        # Query it back
        messages, total = await repo.find_by_user(
            msg.user_id,
            start=date(2025, 6, 1),
            end=date(2025, 6, 30),
            page_size=10,
            page=0,
        )
        assert total >= 1
        assert any(m.id == msg.id for m in messages)


class TestPostgresMessageRepositoryFindByUser:
    @pytest.mark.asyncio
    async def test_find_by_user_returns_matching_messages(self, test_session: AsyncSession):
        repo = PostgresMessageRepository(test_session)
        msg = _make_message(user_id="find-user-1")
        await repo.save(msg)
        await test_session.commit()

        messages, total = await repo.find_by_user(
            "find-user-1",
            start=date(2025, 6, 1),
            end=date(2025, 6, 30),
            page_size=10,
            page=0,
        )

        assert total >= 1
        assert all(m.user_id == "find-user-1" for m in messages)

    @pytest.mark.asyncio
    async def test_find_by_user_respects_date_range(self, test_session: AsyncSession):
        repo = PostgresMessageRepository(test_session)
        msg = _make_message(
            user_id="date-range-user",
            created_at=datetime(2025, 7, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        await repo.save(msg)
        await test_session.commit()

        # Search in June - should not find July message
        messages, total = await repo.find_by_user(
            "date-range-user",
            start=date(2025, 6, 1),
            end=date(2025, 6, 30),
            page_size=10,
            page=0,
        )

        assert total == 0

    @pytest.mark.asyncio
    async def test_find_by_user_pagination(self, test_session: AsyncSession):
        repo = PostgresMessageRepository(test_session)
        user_id = f"paginate-user-{uuid.uuid4()}"

        # Create 5 messages
        for i in range(5):
            msg = _make_message(
                user_id=user_id,
                created_at=datetime(2025, 6, 15, 12, i, 0, tzinfo=timezone.utc),
            )
            await repo.save(msg)
        await test_session.commit()

        # Get page 0 with size 2
        messages, total = await repo.find_by_user(
            user_id,
            start=date(2025, 6, 1),
            end=date(2025, 6, 30),
            page_size=2,
            page=0,
        )

        assert total == 5
        assert len(messages) == 2

    @pytest.mark.asyncio
    async def test_find_by_user_orders_by_created_at_desc(self, test_session: AsyncSession):
        repo = PostgresMessageRepository(test_session)
        user_id = f"order-user-{uuid.uuid4()}"

        # Create messages with different timestamps
        for i in range(3):
            msg = _make_message(
                user_id=user_id,
                created_at=datetime(2025, 6, 15, 12, i, 0, tzinfo=timezone.utc),
            )
            await repo.save(msg)
        await test_session.commit()

        messages, _ = await repo.find_by_user(
            user_id,
            start=date(2025, 6, 1),
            end=date(2025, 6, 30),
            page_size=10,
            page=0,
        )

        timestamps = [m.created_at for m in messages]
        assert timestamps == sorted(timestamps, reverse=True)


class TestPostgresMessageRepositoryFindByDay:
    @pytest.mark.asyncio
    async def test_find_by_day_returns_messages_for_day(self, test_session: AsyncSession):
        repo = PostgresMessageRepository(test_session)
        msg = _make_message(
            user_id=f"day-user-{uuid.uuid4()}",
            created_at=datetime(2025, 6, 20, 12, 0, 0, tzinfo=timezone.utc),
        )
        await repo.save(msg)
        await test_session.commit()

        messages, total = await repo.find_by_day(
            day=date(2025, 6, 20),
            page_size=10,
            page=0,
        )

        assert total >= 1
        assert any(m.id == msg.id for m in messages)

    @pytest.mark.asyncio
    async def test_find_by_day_excludes_other_days(self, test_session: AsyncSession):
        repo = PostgresMessageRepository(test_session)
        msg = _make_message(
            user_id=f"other-day-user-{uuid.uuid4()}",
            created_at=datetime(2025, 6, 21, 12, 0, 0, tzinfo=timezone.utc),
        )
        await repo.save(msg)
        await test_session.commit()

        messages, total = await repo.find_by_day(
            day=date(2025, 6, 20),
            page_size=10,
            page=0,
        )

        assert not any(m.id == msg.id for m in messages)


class TestPostgresMessageRepositoryFindByPeriod:
    @pytest.mark.asyncio
    async def test_find_by_period_returns_messages_in_range(self, test_session: AsyncSession):
        repo = PostgresMessageRepository(test_session)
        msg = _make_message(
            user_id=f"period-user-{uuid.uuid4()}",
            created_at=datetime(2025, 8, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        await repo.save(msg)
        await test_session.commit()

        messages, total = await repo.find_by_period(
            start=date(2025, 8, 1),
            end=date(2025, 8, 31),
            page_size=10,
            page=0,
        )

        assert total >= 1
        assert any(m.id == msg.id for m in messages)

    @pytest.mark.asyncio
    async def test_find_by_period_excludes_outside_range(self, test_session: AsyncSession):
        repo = PostgresMessageRepository(test_session)
        msg = _make_message(
            user_id=f"outside-period-{uuid.uuid4()}",
            created_at=datetime(2025, 9, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        await repo.save(msg)
        await test_session.commit()

        messages, total = await repo.find_by_period(
            start=date(2025, 8, 1),
            end=date(2025, 8, 31),
            page_size=10,
            page=0,
        )

        assert not any(m.id == msg.id for m in messages)


class TestPostgresMessageRepositoryDeleteByUser:
    @pytest.mark.asyncio
    async def test_delete_by_user_removes_messages(self, test_session: AsyncSession):
        repo = PostgresMessageRepository(test_session)
        user_id = f"delete-user-{uuid.uuid4()}"
        msg = _make_message(user_id=user_id)
        await repo.save(msg)
        await test_session.commit()

        await repo.delete_by_user(user_id)
        await test_session.commit()

        messages, total = await repo.find_by_user(
            user_id,
            start=date(2025, 1, 1),
            end=date(2025, 12, 31),
            page_size=10,
            page=0,
        )

        assert total == 0

    @pytest.mark.asyncio
    async def test_delete_by_user_only_deletes_specified_user(self, test_session: AsyncSession):
        repo = PostgresMessageRepository(test_session)
        user_to_delete = f"to-delete-{uuid.uuid4()}"
        user_to_keep = f"to-keep-{uuid.uuid4()}"

        await repo.save(_make_message(user_id=user_to_delete))
        await repo.save(_make_message(user_id=user_to_keep))
        await test_session.commit()

        await repo.delete_by_user(user_to_delete)
        await test_session.commit()

        messages, total = await repo.find_by_user(
            user_to_keep,
            start=date(2025, 1, 1),
            end=date(2025, 12, 31),
            page_size=10,
            page=0,
        )

        assert total >= 1
