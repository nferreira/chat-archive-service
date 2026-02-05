"""Tests for request context management."""
from __future__ import annotations

import structlog

from chat_archive.infrastructure.request_context import (
    CLIENT_ID_HEADER,
    REQUEST_ID_HEADER,
    bind_request_context,
    clear_request_context,
    get_client_id,
    get_request_id,
    set_client_id,
    set_request_id,
)


class TestRequestIdContext:
    def test_get_request_id_returns_none_by_default(self):
        clear_request_context()
        assert get_request_id() is None

    def test_set_request_id_with_value(self):
        clear_request_context()
        result = set_request_id("my-request-id")
        assert result == "my-request-id"
        assert get_request_id() == "my-request-id"

    def test_set_request_id_generates_id_when_none(self):
        clear_request_context()
        result = set_request_id(None)
        assert result is not None
        assert len(result) == 8  # UUID first 8 chars
        assert get_request_id() == result

    def test_set_request_id_generates_id_when_not_provided(self):
        clear_request_context()
        result = set_request_id()
        assert result is not None
        assert len(result) == 8


class TestClientIdContext:
    def test_get_client_id_returns_none_by_default(self):
        clear_request_context()
        assert get_client_id() is None

    def test_set_client_id_with_value(self):
        clear_request_context()
        result = set_client_id("my-client-id")
        assert result == "my-client-id"
        assert get_client_id() == "my-client-id"

    def test_set_client_id_generates_id_when_none(self):
        clear_request_context()
        result = set_client_id(None)
        assert result is not None
        assert len(result) == 8
        assert get_client_id() == result


class TestClearRequestContext:
    def test_clears_request_id(self):
        set_request_id("test-rid")
        set_client_id("test-cid")
        clear_request_context()
        assert get_request_id() is None
        assert get_client_id() is None


class TestBindRequestContext:
    def test_binds_context_to_structlog(self):
        clear_request_context()
        bind_request_context(user_id="u123", operation="test")
        # Verify context is bound by checking structlog contextvars
        ctx = structlog.contextvars.get_contextvars()
        assert ctx.get("user_id") == "u123"
        assert ctx.get("operation") == "test"
        clear_request_context()


class TestHeaderConstants:
    def test_request_id_header_name(self):
        assert REQUEST_ID_HEADER == "X-Request-ID"

    def test_client_id_header_name(self):
        assert CLIENT_ID_HEADER == "X-Client-ID"
