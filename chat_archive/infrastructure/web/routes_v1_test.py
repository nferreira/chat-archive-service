from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from chat_archive.container import get_session
from chat_archive.infrastructure.db.orm import Base
from chat_archive.main import app

# Use SQLite for integration tests (in-memory)
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


@pytest.fixture
async def client(test_session):
    async def override_get_session():
        yield test_session

    app.fastapi.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.fastapi.dependency_overrides.clear()


class TestStoreMessage:
    @pytest.mark.asyncio
    async def test_store_returns_201(self, client):
        resp = await client.post(
            "/api/v1/messages",
            json={
                "user_id": "u1",
                "name": "Alice",
                "question": "What?",
                "answer": "That.",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "created_at" in data
        # Validate UUID
        uuid.UUID(data["id"])

    @pytest.mark.asyncio
    async def test_store_missing_field_returns_422(self, client):
        resp = await client.post(
            "/api/v1/messages",
            json={"user_id": "u1", "name": "Alice"},
        )
        assert resp.status_code == 422


class TestGetMessagesByUser:
    @pytest.mark.asyncio
    async def test_returns_messages_without_private_fields(self, client):
        # Store a message first
        await client.post(
            "/api/v1/messages",
            json={
                "user_id": "u-privacy",
                "name": "Secret",
                "question": "Q1",
                "answer": "A1",
            },
        )
        today = datetime.now(timezone.utc).date().isoformat()
        resp = await client.get(f"/api/v1/users/u-privacy/messages?start={today}&end={today}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert "page_size" in data
        assert "page" in data
        for item in data["items"]:
            assert "user_id" not in item
            assert "name" not in item
            assert "question" in item
            assert "answer" in item
            assert "created_at" in item

    @pytest.mark.asyncio
    async def test_pagination_params_empty_returns_204_with_headers(self, client):
        resp = await client.get("/api/v1/users/u-none/messages?start=2020-01-01&end=2020-12-31&page_size=10&page=0")
        assert resp.status_code == 204
        assert resp.headers["X-Page-Size"] == "10"
        assert resp.headers["X-Page"] == "0"
        assert resp.headers["X-Total-Count"] == "0"

    @pytest.mark.asyncio
    async def test_missing_start_end_returns_422(self, client):
        resp = await client.get("/api/v1/users/u1/messages")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_returns_200_with_items(self, client):
        """Test user messages returns 200 when items exist."""
        uid = "u-user-200"
        today = datetime.now(timezone.utc).date().isoformat()
        await client.post(
            "/api/v1/messages",
            json={
                "user_id": uid,
                "name": "User200",
                "question": "Q",
                "answer": "A",
            },
        )
        resp = await client.get(f"/api/v1/users/{uid}/messages?start={today}&end={today}")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1


class TestGetMessagesByDay:
    @pytest.mark.asyncio
    async def test_empty_day_returns_204_with_headers(self, client):
        resp = await client.get("/api/v1/messages?day=2025-06-15")
        assert resp.status_code == 204
        assert "X-Total-Count" in resp.headers
        assert "X-Page-Size" in resp.headers
        assert "X-Page" in resp.headers

    @pytest.mark.asyncio
    async def test_day_with_start_returns_422(self, client):
        """Cannot combine day with start parameter."""
        resp = await client.get("/api/v1/messages?day=2025-06-15&start=2025-06-01")
        assert resp.status_code == 422
        assert "Cannot combine" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_day_with_end_returns_422(self, client):
        """Cannot combine day with end parameter."""
        resp = await client.get("/api/v1/messages?day=2025-06-15&end=2025-06-30")
        assert resp.status_code == 422
        assert "Cannot combine" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_day_with_start_and_end_returns_422(self, client):
        """Cannot combine day with both start and end parameters."""
        resp = await client.get("/api/v1/messages?day=2025-06-15&start=2025-06-01&end=2025-06-30")
        assert resp.status_code == 422
        assert "Cannot combine" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_day_returns_200_with_items(self, client):
        """Test day query returns 200 when items exist."""
        # Store a message for today
        today = datetime.now(timezone.utc).date().isoformat()
        await client.post(
            "/api/v1/messages",
            json={
                "user_id": "u-day-200",
                "name": "DayUser200",
                "question": "Q",
                "answer": "A",
            },
        )
        resp = await client.get(f"/api/v1/messages?day={today}")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_items_privacy(self, client):
        # Store a message for today
        await client.post(
            "/api/v1/messages",
            json={
                "user_id": "u-day-privacy",
                "name": "DayUser",
                "question": "Q",
                "answer": "A",
            },
        )
        today = datetime.now(timezone.utc).date().isoformat()
        resp = await client.get(f"/api/v1/messages?day={today}")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert "user_id" not in item
            assert "name" not in item

    @pytest.mark.asyncio
    async def test_no_filter_params_returns_422(self, client):
        resp = await client.get("/api/v1/messages")
        assert resp.status_code == 422


class TestGetMessagesByPeriod:
    @pytest.mark.asyncio
    async def test_empty_period_returns_204_with_headers(self, client):
        resp = await client.get(
            "/api/v1/messages?start=2020-01-01&end=2020-12-31"
        )
        assert resp.status_code == 204
        assert "X-Total-Count" in resp.headers
        assert "X-Page-Size" in resp.headers
        assert "X-Page" in resp.headers

    @pytest.mark.asyncio
    async def test_period_returns_200_with_items(self, client):
        """Test period query returns 200 when items exist."""
        today = datetime.now(timezone.utc).date().isoformat()
        await client.post(
            "/api/v1/messages",
            json={
                "user_id": "u-period-200",
                "name": "PeriodUser200",
                "question": "Q",
                "answer": "A",
            },
        )
        resp = await client.get(f"/api/v1/messages?start={today}&end={today}")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_missing_end_param(self, client):
        resp = await client.get("/api/v1/messages?start=2025-01-01")
        assert resp.status_code == 422


class TestDeleteUser:
    @pytest.mark.asyncio
    async def test_delete_returns_204(self, client):
        # Store then delete
        await client.post(
            "/api/v1/messages",
            json={
                "user_id": "u-del",
                "name": "ToDelete",
                "question": "Q",
                "answer": "A",
            },
        )
        resp = await client.delete("/api/v1/users/u-del")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_after_delete_user_has_no_messages(self, client):
        uid = "u-cascade"
        await client.post(
            "/api/v1/messages",
            json={
                "user_id": uid,
                "name": "CascadeUser",
                "question": "Q",
                "answer": "A",
            },
        )
        await client.delete(f"/api/v1/users/{uid}")
        today = datetime.now(timezone.utc).date().isoformat()
        resp = await client.get(f"/api/v1/users/{uid}/messages?start={today}&end={today}")
        assert resp.status_code == 204
        assert resp.headers["X-Total-Count"] == "0"


class TestOrdering:
    @pytest.mark.asyncio
    async def test_messages_ordered_by_created_at_desc(self, client):
        uid = "u-order"
        for i in range(3):
            await client.post(
                "/api/v1/messages",
                json={
                    "user_id": uid,
                    "name": "OrderUser",
                    "question": f"Q{i}",
                    "answer": f"A{i}",
                },
            )
        today = datetime.now(timezone.utc).date().isoformat()
        resp = await client.get(f"/api/v1/users/{uid}/messages?start={today}&end={today}")
        items = resp.json()["items"]
        timestamps = [item["created_at"] for item in items]
        assert timestamps == sorted(timestamps, reverse=True)


class TestRoutesDirect:
    """Direct unit tests for route functions to ensure coverage."""

    @pytest.mark.asyncio
    async def test_store_message_direct(self, test_session):
        """Test store_message route function directly."""
        from unittest.mock import AsyncMock
        from chat_archive.infrastructure.web.routes_v1 import store_message
        from chat_archive.application.store_message.models import StoreMessageRequest
        from chat_archive.application.store_message.use_case import StoreMessageUseCase
        from chat_archive.infrastructure.db.repositories.message_repository_pg import PostgresMessageRepository

        repo = PostgresMessageRepository(test_session)
        uc = StoreMessageUseCase(repo)
        body = StoreMessageRequest(
            user_id="u-direct",
            name="Direct",
            question="Q",
            answer="A",
        )

        result = await store_message(body=body, session=test_session, uc=uc)

        assert result.id is not None
        assert result.created_at is not None

    @pytest.mark.asyncio
    async def test_get_messages_by_day_direct(self, test_session):
        """Test get_messages route function directly with day parameter."""
        from chat_archive.infrastructure.web.routes_v1 import get_messages
        from chat_archive.infrastructure.db.repositories.message_repository_pg import PostgresMessageRepository

        repo = PostgresMessageRepository(test_session)
        today = datetime.now(timezone.utc).date()

        result = await get_messages(
            day=today,
            start=None,
            end=None,
            page_size=50,
            page=0,
            repo=repo,
        )

        # Returns either a Response (204) or the result object
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_messages_by_period_direct(self, test_session):
        """Test get_messages route function directly with period parameters."""
        from chat_archive.infrastructure.web.routes_v1 import get_messages
        from chat_archive.infrastructure.db.repositories.message_repository_pg import PostgresMessageRepository

        repo = PostgresMessageRepository(test_session)
        today = datetime.now(timezone.utc).date()

        result = await get_messages(
            day=None,
            start=today,
            end=today,
            page_size=50,
            page=0,
            repo=repo,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_messages_by_user_direct(self, test_session):
        """Test get_messages_by_user route function directly."""
        from chat_archive.infrastructure.web.routes_v1 import get_messages_by_user
        from chat_archive.application.get_messages_by_user.use_case import GetMessagesByUserUseCase
        from chat_archive.infrastructure.db.repositories.message_repository_pg import PostgresMessageRepository

        repo = PostgresMessageRepository(test_session)
        uc = GetMessagesByUserUseCase(repo)
        today = datetime.now(timezone.utc).date()

        result = await get_messages_by_user(
            user_id="u-direct-user",
            start=today,
            end=today,
            page_size=50,
            page=0,
            uc=uc,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_delete_user_direct(self, test_session):
        """Test delete_user route function directly."""
        from chat_archive.infrastructure.web.routes_v1 import delete_user, store_message
        from chat_archive.application.delete_user.use_case import DeleteUserUseCase
        from chat_archive.application.store_message.models import StoreMessageRequest
        from chat_archive.application.store_message.use_case import StoreMessageUseCase
        from chat_archive.infrastructure.db.repositories.message_repository_pg import PostgresMessageRepository

        repo = PostgresMessageRepository(test_session)

        # First store a message
        store_uc = StoreMessageUseCase(repo)
        body = StoreMessageRequest(
            user_id="u-delete-direct",
            name="DeleteDirect",
            question="Q",
            answer="A",
        )
        await store_message(body=body, session=test_session, uc=store_uc)

        # Then delete
        delete_uc = DeleteUserUseCase(repo)
        result = await delete_user(
            user_id="u-delete-direct",
            session=test_session,
            uc=delete_uc,
        )

        assert result.status_code == 204
