"""Tests for store_message models."""
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from chat_archive.application.store_message.models import (
    StoreMessageRequest,
    StoreMessageResponse,
)


class TestStoreMessageRequest:
    def test_valid_request(self):
        req = StoreMessageRequest(
            user_id="user-1",
            name="Alice",
            question="What is Python?",
            answer="A programming language.",
        )

        assert req.user_id == "user-1"
        assert req.name == "Alice"
        assert req.question == "What is Python?"
        assert req.answer == "A programming language."

    def test_missing_user_id_raises(self):
        with pytest.raises(ValidationError):
            StoreMessageRequest(
                name="Alice",
                question="Q",
                answer="A",
            )

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            StoreMessageRequest(
                user_id="u1",
                question="Q",
                answer="A",
            )

    def test_missing_question_raises(self):
        with pytest.raises(ValidationError):
            StoreMessageRequest(
                user_id="u1",
                name="Alice",
                answer="A",
            )

    def test_missing_answer_raises(self):
        with pytest.raises(ValidationError):
            StoreMessageRequest(
                user_id="u1",
                name="Alice",
                question="Q",
            )

    def test_empty_strings_are_valid(self):
        # Pydantic allows empty strings by default
        req = StoreMessageRequest(
            user_id="",
            name="",
            question="",
            answer="",
        )
        assert req.user_id == ""

    def test_model_dump(self):
        req = StoreMessageRequest(
            user_id="u1",
            name="Bob",
            question="Q?",
            answer="A.",
        )
        data = req.model_dump()

        assert data == {
            "user_id": "u1",
            "name": "Bob",
            "question": "Q?",
            "answer": "A.",
        }


class TestStoreMessageResponse:
    def test_valid_response(self):
        msg_id = uuid.uuid4()
        resp = StoreMessageResponse(
            id=msg_id,
            created_at="2025-06-15T12:00:00Z",
        )

        assert resp.id == msg_id
        assert resp.created_at == "2025-06-15T12:00:00Z"

    def test_response_serialization(self):
        msg_id = uuid.uuid4()
        resp = StoreMessageResponse(
            id=msg_id,
            created_at="2025-06-15T12:00:00+00:00",
        )
        data = resp.model_dump()

        assert "id" in data
        assert "created_at" in data
        assert data["id"] == msg_id

    def test_response_json_serialization(self):
        msg_id = uuid.uuid4()
        resp = StoreMessageResponse(
            id=msg_id,
            created_at="2025-06-15T12:00:00Z",
        )
        json_str = resp.model_dump_json()

        assert str(msg_id) in json_str
        assert "2025-06-15T12:00:00Z" in json_str

    def test_missing_id_raises(self):
        with pytest.raises(ValidationError):
            StoreMessageResponse(created_at="2025-06-15T12:00:00Z")

    def test_missing_created_at_raises(self):
        with pytest.raises(ValidationError):
            StoreMessageResponse(id=uuid.uuid4())
