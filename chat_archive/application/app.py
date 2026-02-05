from __future__ import annotations

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response

from sqlalchemy import text

from chat_archive.container import Container
from chat_archive.infrastructure.db.engine import DATABASE_URL, _mask_password
from chat_archive.infrastructure.logging import setup_logging
from chat_archive.infrastructure.request_context import (
    CLIENT_ID_HEADER,
    REQUEST_ID_HEADER,
    bind_request_context,
    clear_request_context,
    set_client_id,
    set_request_id,
)
from chat_archive.infrastructure.web.routes_v1 import router as v1_router

# Configure logging early so all logs use consistent formatting
setup_logging()
log = structlog.stdlib.get_logger()


class App:
    def __init__(self) -> None:
        self._container = Container()
        self._container.config.database_url.from_value(DATABASE_URL)
        self._container.wire()
        log.info("app.db.configured", url=_mask_password(DATABASE_URL))

        self._fastapi = FastAPI(
            title="Chat Archive Service",
            description="""
Chat Archive Service API for storing and retrieving chat messages.

## Features

* **Store Messages** - Archive chat messages with user information
* **Query by User** - Retrieve messages for a specific user within a date range
* **Query by Day** - Retrieve all messages for a specific day
* **Query by Period** - Retrieve all messages within a date range
* **Delete User Data** - GDPR-compliant user data deletion

## Privacy

Query responses exclude sensitive fields (`user_id`, `name`) to protect user privacy.
Only the message content (`question`, `answer`) and timestamp are returned.
            """,
            version="1.0.0",
            contact={
                "name": "API Support",
                "email": "support@example.com",
            },
            license_info={
                "name": "MIT",
            },
            openapi_tags=[
                {
                    "name": "messages",
                    "description": "Operations for storing and querying chat messages",
                },
                {
                    "name": "users",
                    "description": "User-specific operations including data retrieval and deletion",
                },
                {
                    "name": "health",
                    "description": "Health check endpoints for monitoring",
                },
            ],
            lifespan=self._lifespan,
        )
        self._fastapi.include_router(v1_router)
        self._fastapi.middleware("http")(self._logging_middleware)
        self._fastapi.get(
            "/health",
            tags=["health"],
            summary="Health check",
            response_description="Service health status",
        )(self._health_check)

    @property
    def fastapi(self) -> FastAPI:
        return self._fastapi

    @property
    def container(self) -> Container:
        return self._container

    async def __call__(self, scope, receive, send) -> None:
        await self._fastapi(scope, receive, send)

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        log.info("app.started")
        yield
        await self._container.engine().dispose()
        log.info("app.shutdown")

    async def _health_check(self) -> dict:
        """Health check endpoint for Docker/Kubernetes liveness probes."""
        async with self._container.engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy"}

    @staticmethod
    async def _logging_middleware(request: Request, call_next) -> Response:
        # Extract or generate correlation IDs from headers
        # Headers are case-insensitive, FastAPI normalizes to lowercase
        request_id = set_request_id(request.headers.get(REQUEST_ID_HEADER.lower()))
        client_id = set_client_id(request.headers.get(CLIENT_ID_HEADER.lower()))

        # Bind context for all log entries in this request
        bind_request_context(
            request_id=request_id,
            client_id=client_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

            # Log level based on status code for easier filtering
            if response.status_code >= 500:
                log.error(
                    "request.completed",
                    status_code=response.status_code,
                    elapsed_ms=elapsed_ms,
                )
            elif response.status_code >= 400:
                log.warning(
                    "request.completed",
                    status_code=response.status_code,
                    elapsed_ms=elapsed_ms,
                )
            else:
                log.info(
                    "request.completed",
                    status_code=response.status_code,
                    elapsed_ms=elapsed_ms,
                )

            # Add correlation IDs to response headers for client correlation
            response.headers[REQUEST_ID_HEADER] = request_id
            response.headers[CLIENT_ID_HEADER] = client_id
            return response
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            log.error(
                "request.failed",
                elapsed_ms=elapsed_ms,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
        finally:
            clear_request_context()
