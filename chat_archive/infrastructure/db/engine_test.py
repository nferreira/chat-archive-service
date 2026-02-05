"""Tests for database engine configuration."""
from __future__ import annotations

import os
from unittest.mock import patch

from chat_archive.infrastructure.db.engine import DATABASE_URL, _mask_password


class TestDatabaseUrl:
    def test_default_database_url_is_set(self):
        # DATABASE_URL should have a default value
        assert DATABASE_URL is not None
        assert "postgresql" in DATABASE_URL or os.environ.get("DATABASE_URL") is not None

    def test_database_url_from_env_var(self):
        # The module reads from env at import time, so we verify the pattern
        # by checking _mask_password works with different URL formats
        test_url = "postgresql+psycopg://user:pass@host:5432/db"
        masked = _mask_password(test_url)
        assert "***" in masked


class TestMaskPassword:
    def test_masks_password_in_url(self):
        url = "postgresql+psycopg://myuser:secretpassword@localhost:5432/mydb"
        result = _mask_password(url)
        assert result == "postgresql+psycopg://myuser:***@localhost:5432/mydb"

    def test_masks_password_with_special_chars(self):
        url = "postgresql://user:p@ss!word@host:5432/db"
        result = _mask_password(url)
        # The regex matches until @ so special chars before @ are part of password
        assert "***" in result
        assert "p@ss!word" not in result

    def test_handles_url_without_password(self):
        url = "postgresql://host:5432/db"
        result = _mask_password(url)
        # Should return the URL unchanged
        assert result == url

    def test_preserves_username(self):
        url = "postgresql+psycopg://admin:topsecret@db.example.com:5432/prod"
        result = _mask_password(url)
        assert "admin" in result
        assert "topsecret" not in result

    def test_handles_sqlite_url(self):
        url = "sqlite:///path/to/db.sqlite"
        result = _mask_password(url)
        assert result == url

    def test_handles_memory_sqlite(self):
        url = "sqlite+aiosqlite:///file::memory:?cache=shared"
        result = _mask_password(url)
        assert result == url
