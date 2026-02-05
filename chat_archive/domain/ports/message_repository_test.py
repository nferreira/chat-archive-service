"""Tests for the MessageRepository protocol."""
from __future__ import annotations

import abc
import inspect
from datetime import date

from chat_archive.domain.models.message import Message
from chat_archive.domain.ports.message_repository import MessageRepository


class TestMessageRepositoryProtocol:
    def test_is_abstract_base_class(self):
        assert issubclass(MessageRepository, abc.ABC)

    def test_save_is_abstract(self):
        assert hasattr(MessageRepository, "save")
        method = getattr(MessageRepository, "save")
        assert getattr(method, "__isabstractmethod__", False)

    def test_find_by_user_is_abstract(self):
        assert hasattr(MessageRepository, "find_by_user")
        method = getattr(MessageRepository, "find_by_user")
        assert getattr(method, "__isabstractmethod__", False)

    def test_find_by_day_is_abstract(self):
        assert hasattr(MessageRepository, "find_by_day")
        method = getattr(MessageRepository, "find_by_day")
        assert getattr(method, "__isabstractmethod__", False)

    def test_find_by_period_is_abstract(self):
        assert hasattr(MessageRepository, "find_by_period")
        method = getattr(MessageRepository, "find_by_period")
        assert getattr(method, "__isabstractmethod__", False)

    def test_delete_by_user_is_abstract(self):
        assert hasattr(MessageRepository, "delete_by_user")
        method = getattr(MessageRepository, "delete_by_user")
        assert getattr(method, "__isabstractmethod__", False)

    def test_save_signature(self):
        sig = inspect.signature(MessageRepository.save)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "message" in params

    def test_find_by_user_signature(self):
        sig = inspect.signature(MessageRepository.find_by_user)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "user_id" in params
        assert "start" in params
        assert "end" in params
        assert "page_size" in params
        assert "page" in params

    def test_find_by_day_signature(self):
        sig = inspect.signature(MessageRepository.find_by_day)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "day" in params
        assert "page_size" in params
        assert "page" in params

    def test_find_by_period_signature(self):
        sig = inspect.signature(MessageRepository.find_by_period)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "start" in params
        assert "end" in params
        assert "page_size" in params
        assert "page" in params

    def test_delete_by_user_signature(self):
        sig = inspect.signature(MessageRepository.delete_by_user)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "user_id" in params
