"""Shared test fixtures for the chat_archive package."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from chat_archive.domain.models.message import Message
from chat_archive.infrastructure.db.orm import Base

# Use SQLite for integration tests (in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///data/file::memory:?cache=shared"


def make_message(**overrides) -> Message:
    """Factory for creating test Message objects with sensible defaults."""
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


@pytest.fixture
def mock_repo():
    """Async mock repository for unit tests."""
    return AsyncMock()


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def test_engine():
    """Create an in-memory SQLite engine for integration tests."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create a database session with automatic rollback after each test."""
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
