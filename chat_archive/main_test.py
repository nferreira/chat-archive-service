"""Tests for the main module."""
from __future__ import annotations


class TestMainModule:
    def test_app_is_importable(self):
        from chat_archive.main import app
        assert app is not None

    def test_app_has_fastapi_attribute(self):
        from chat_archive.main import app
        assert hasattr(app, "fastapi")

    def test_app_is_callable(self):
        from chat_archive.main import app
        assert callable(app)

    def test_app_is_app_instance(self):
        from chat_archive.main import app
        from chat_archive.application.app import App
        assert isinstance(app, App)
