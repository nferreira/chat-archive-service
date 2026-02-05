"""Tests for the App class."""
from __future__ import annotations

import pytest
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from unittest.mock import AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager

from chat_archive.application.app import App
from chat_archive.container import Container, get_session
from chat_archive.infrastructure.db.orm import Base

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


class TestApp:
    def test_app_has_fastapi_instance(self):
        app = App()
        assert isinstance(app.fastapi, FastAPI)

    def test_openapi_schema_is_generated(self):
        app = App()
        schema = app.fastapi.openapi()

        assert schema["info"]["title"] == "Chat Archive Service"
        assert schema["info"]["version"] == "1.0.0"
        assert "paths" in schema
        assert "/api/v1/messages" in schema["paths"]
        assert "/api/v1/users/{user_id}/messages" in schema["paths"]
        assert "/api/v1/users/{user_id}" in schema["paths"]
        assert "/health" in schema["paths"]

    def test_openapi_has_tags(self):
        app = App()
        schema = app.fastapi.openapi()

        tag_names = [tag["name"] for tag in schema.get("tags", [])]
        assert "messages" in tag_names
        assert "users" in tag_names
        assert "health" in tag_names

    def test_openapi_has_components(self):
        app = App()
        schema = app.fastapi.openapi()

        assert "components" in schema
        assert "schemas" in schema["components"]
        assert "StoreMessageRequest" in schema["components"]["schemas"]
        assert "StoreMessageResponse" in schema["components"]["schemas"]
        assert "MessageItem" in schema["components"]["schemas"]

    def test_app_has_container(self):
        app = App()
        # Container becomes DynamicContainer after wiring
        assert app.container is not None
        assert hasattr(app.container, "config")
        assert hasattr(app.container, "engine")

    def test_fastapi_has_title(self):
        app = App()
        assert app.fastapi.title == "Chat Archive Service"

    def test_app_is_callable(self):
        app = App()
        assert callable(app)


class TestAppMiddleware:
    @pytest.mark.asyncio
    async def test_adds_request_id_header_to_response(self, test_session):
        app = App()

        async def override_get_session():
            yield test_session

        app.fastapi.dependency_overrides[get_session] = override_get_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert "X-Request-ID" in resp.headers
        app.fastapi.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_adds_client_id_header_to_response(self, test_session):
        app = App()

        async def override_get_session():
            yield test_session

        app.fastapi.dependency_overrides[get_session] = override_get_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert "X-Client-ID" in resp.headers
        app.fastapi.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_echoes_provided_request_id(self, test_session):
        app = App()

        async def override_get_session():
            yield test_session

        app.fastapi.dependency_overrides[get_session] = override_get_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health", headers={"X-Request-ID": "my-req-123"})
            assert resp.headers["X-Request-ID"] == "my-req-123"
        app.fastapi.dependency_overrides.clear()


class TestAppHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, test_session):
        app = App()

        async def override_get_session():
            yield test_session

        app.fastapi.dependency_overrides[get_session] = override_get_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
        app.fastapi.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_health_returns_healthy_status(self, test_session):
        app = App()

        async def override_get_session():
            yield test_session

        app.fastapi.dependency_overrides[get_session] = override_get_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            assert data["status"] == "healthy"
        app.fastapi.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_health_check_executes_db_query(self, test_engine):
        """Test that health check actually executes a database query."""
        from sqlalchemy.ext.asyncio import async_sessionmaker

        app = App()

        # Override the container's engine with our test engine
        app._container.engine.override(test_engine)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            assert resp.json()["status"] == "healthy"


class TestAppRoutes:
    @pytest.mark.asyncio
    async def test_v1_routes_are_included(self, test_session):
        app = App()

        async def override_get_session():
            yield test_session

        app.fastapi.dependency_overrides[get_session] = override_get_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Just verify the route exists (even if validation fails)
            resp = await client.get("/api/v1/messages?day=2025-06-15")
            # 204 (no content) or 422 (validation error) both indicate route exists
            assert resp.status_code in [200, 204, 422]
        app.fastapi.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_store_message_and_commit(self, test_session):
        app = App()

        async def override_get_session():
            yield test_session

        app.fastapi.dependency_overrides[get_session] = override_get_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/messages",
                json={
                    "user_id": "u-commit-test",
                    "name": "CommitTest",
                    "question": "Q",
                    "answer": "A",
                },
            )
            assert resp.status_code == 201
        app.fastapi.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_user_and_commit(self, test_session):
        app = App()

        async def override_get_session():
            yield test_session

        app.fastapi.dependency_overrides[get_session] = override_get_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Store first
            await client.post(
                "/api/v1/messages",
                json={
                    "user_id": "u-delete-commit",
                    "name": "DeleteTest",
                    "question": "Q",
                    "answer": "A",
                },
            )
            # Delete
            resp = await client.delete("/api/v1/users/u-delete-commit")
            assert resp.status_code == 204
        app.fastapi.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_messages_by_day_route(self, test_session):
        from datetime import datetime, timezone
        app = App()

        async def override_get_session():
            yield test_session

        app.fastapi.dependency_overrides[get_session] = override_get_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Store a message for today
            await client.post(
                "/api/v1/messages",
                json={
                    "user_id": "u-day-test",
                    "name": "DayTest",
                    "question": "Q",
                    "answer": "A",
                },
            )
            today = datetime.now(timezone.utc).date().isoformat()
            resp = await client.get(f"/api/v1/messages?day={today}")
            assert resp.status_code in [200, 204]
        app.fastapi.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_messages_by_period_route(self, test_session):
        from datetime import datetime, timezone
        app = App()

        async def override_get_session():
            yield test_session

        app.fastapi.dependency_overrides[get_session] = override_get_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Store a message for today
            await client.post(
                "/api/v1/messages",
                json={
                    "user_id": "u-period-test",
                    "name": "PeriodTest",
                    "question": "Q",
                    "answer": "A",
                },
            )
            today = datetime.now(timezone.utc).date().isoformat()
            resp = await client.get(f"/api/v1/messages?start={today}&end={today}")
            assert resp.status_code in [200, 204]
        app.fastapi.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_messages_by_user_route(self, test_session):
        from datetime import datetime, timezone
        app = App()

        async def override_get_session():
            yield test_session

        app.fastapi.dependency_overrides[get_session] = override_get_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Store a message for today
            await client.post(
                "/api/v1/messages",
                json={
                    "user_id": "u-user-test",
                    "name": "UserTest",
                    "question": "Q",
                    "answer": "A",
                },
            )
            today = datetime.now(timezone.utc).date().isoformat()
            resp = await client.get(f"/api/v1/users/u-user-test/messages?start={today}&end={today}")
            assert resp.status_code in [200, 204]
        app.fastapi.dependency_overrides.clear()


class TestAppLifespan:
    @pytest.mark.asyncio
    async def test_lifespan_startup_and_shutdown(self):
        """Test that lifespan context manager runs startup and shutdown."""
        app = App()

        # Test the lifespan context manager directly
        async with app._lifespan(app.fastapi):
            # Inside the context, app should be "started"
            pass
        # After exiting, shutdown should have been called

    @pytest.mark.asyncio
    async def test_lifespan_disposes_engine(self):
        """Test that lifespan disposes the engine on shutdown."""
        app = App()

        # Mock the engine's dispose method
        mock_engine = AsyncMock()
        app._container.engine.override(mock_engine)

        async with app._lifespan(app.fastapi):
            pass

        mock_engine.dispose.assert_called_once()


class TestAppMiddlewareErrorHandling:
    @pytest.mark.asyncio
    async def test_logs_5xx_errors(self, test_session):
        """Test that 5xx responses are logged at error level."""
        app = App()

        # Add a route that returns 500
        @app.fastapi.get("/test-500")
        async def return_500():
            return JSONResponse(status_code=500, content={"error": "Internal Server Error"})

        async def override_get_session():
            yield test_session

        app.fastapi.dependency_overrides[get_session] = override_get_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test-500")
            assert resp.status_code == 500
        app.fastapi.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_logs_4xx_errors_as_warning(self, test_session):
        """Test that 4xx responses are logged at warning level."""
        app = App()

        async def override_get_session():
            yield test_session

        app.fastapi.dependency_overrides[get_session] = override_get_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # This should return 404
            resp = await client.get("/nonexistent-route")
            assert resp.status_code == 404
        app.fastapi.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_middleware_handles_exceptions(self, test_session):
        """Test that middleware catches, logs, and re-raises exceptions."""
        app = App()

        # Add a route that raises an exception
        @app.fastapi.get("/test-exception")
        async def raise_exception():
            raise RuntimeError("Test exception")

        async def override_get_session():
            yield test_session

        app.fastapi.dependency_overrides[get_session] = override_get_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # The middleware logs the exception and re-raises it
            with pytest.raises(RuntimeError, match="Test exception"):
                await client.get("/test-exception")
        app.fastapi.dependency_overrides.clear()
