"""Tests for get_messages_by_day models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from chat_archive.application.get_messages_by_day.models import (
    GetMessagesByDayResponse,
    MessageItem,
)


class TestMessageItem:
    def test_valid_item(self):
        item = MessageItem(
            question="What is Python?",
            answer="A programming language.",
            created_at="2025-06-15T12:00:00Z",
        )

        assert item.question == "What is Python?"
        assert item.answer == "A programming language."
        assert item.created_at == "2025-06-15T12:00:00Z"

    def test_missing_question_raises(self):
        with pytest.raises(ValidationError):
            MessageItem(
                answer="A.",
                created_at="2025-06-15T12:00:00Z",
            )

    def test_missing_answer_raises(self):
        with pytest.raises(ValidationError):
            MessageItem(
                question="Q?",
                created_at="2025-06-15T12:00:00Z",
            )

    def test_missing_created_at_raises(self):
        with pytest.raises(ValidationError):
            MessageItem(
                question="Q?",
                answer="A.",
            )

    def test_does_not_have_user_id(self):
        item = MessageItem(
            question="Q",
            answer="A",
            created_at="2025-06-15T12:00:00Z",
        )
        data = item.model_dump()
        assert "user_id" not in data

    def test_does_not_have_name(self):
        item = MessageItem(
            question="Q",
            answer="A",
            created_at="2025-06-15T12:00:00Z",
        )
        data = item.model_dump()
        assert "name" not in data


class TestGetMessagesByDayResponse:
    def test_valid_response(self):
        resp = GetMessagesByDayResponse(
            items=[
                MessageItem(question="Q1", answer="A1", created_at="2025-06-15T12:00:00Z"),
            ],
            total=1,
            page_size=50,
            page=0,
        )

        assert len(resp.items) == 1
        assert resp.total == 1
        assert resp.page_size == 50
        assert resp.page == 0

    def test_empty_items(self):
        resp = GetMessagesByDayResponse(
            items=[],
            total=0,
            page_size=50,
            page=0,
        )

        assert resp.items == []
        assert resp.total == 0

    def test_missing_items_raises(self):
        with pytest.raises(ValidationError):
            GetMessagesByDayResponse(
                total=0,
                page_size=50,
                page=0,
            )

    def test_missing_total_raises(self):
        with pytest.raises(ValidationError):
            GetMessagesByDayResponse(
                items=[],
                page_size=50,
                page=0,
            )

    def test_missing_page_size_raises(self):
        with pytest.raises(ValidationError):
            GetMessagesByDayResponse(
                items=[],
                total=0,
                page=0,
            )

    def test_missing_page_raises(self):
        with pytest.raises(ValidationError):
            GetMessagesByDayResponse(
                items=[],
                total=0,
                page_size=50,
            )

    def test_response_serialization(self):
        resp = GetMessagesByDayResponse(
            items=[
                MessageItem(question="Q", answer="A", created_at="2025-06-15T12:00:00Z"),
            ],
            total=1,
            page_size=50,
            page=0,
        )
        data = resp.model_dump()

        assert "items" in data
        assert "total" in data
        assert "page_size" in data
        assert "page" in data

    def test_items_privacy_in_serialization(self):
        resp = GetMessagesByDayResponse(
            items=[
                MessageItem(question="Q", answer="A", created_at="2025-06-15T12:00:00Z"),
            ],
            total=1,
            page_size=50,
            page=0,
        )
        data = resp.model_dump()

        for item in data["items"]:
            assert "user_id" not in item
            assert "name" not in item
