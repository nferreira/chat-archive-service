"""Request context management for log correlation.

This module provides a single-responsibility mechanism for binding request-scoped
context (like request_id, client_id) to all log entries within a request lifecycle.
"""
from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Any

import structlog

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_client_id: ContextVar[str | None] = ContextVar("client_id", default=None)

# Header names (case-insensitive in HTTP)
REQUEST_ID_HEADER = "X-Request-ID"
CLIENT_ID_HEADER = "X-Client-ID"


def _generate_id() -> str:
    """Generate a short unique ID."""
    return str(uuid.uuid4())[:8]


def get_request_id() -> str | None:
    """Get the current request ID from context."""
    return _request_id.get()


def get_client_id() -> str | None:
    """Get the current client ID from context."""
    return _client_id.get()


def set_request_id(request_id: str | None = None) -> str:
    """Set a request ID in context. Generates one if not provided."""
    rid = request_id or _generate_id()
    _request_id.set(rid)
    return rid


def set_client_id(client_id: str | None = None) -> str:
    """Set a client ID in context. Generates one if not provided."""
    cid = client_id or _generate_id()
    _client_id.set(cid)
    return cid


def clear_request_context() -> None:
    """Clear the request context."""
    _request_id.set(None)
    _client_id.set(None)
    structlog.contextvars.clear_contextvars()


def bind_request_context(**context: Any) -> None:
    """Bind additional context that will be included in all subsequent log entries.

    Args:
        **context: Key-value pairs to bind to the logging context.

    Example:
        bind_request_context(user_id="abc123", operation="store_message")
    """
    structlog.contextvars.bind_contextvars(**context)
