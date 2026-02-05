"""Tests for the Message domain model."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from chat_archive.domain.models.message import Message


class TestMessage:
    def test_instantiation_with_all_fields(self):
        msg_id = uuid.uuid4()
        created = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        msg = Message(
            id=msg_id,
            user_id="user-123",
            name="Alice",
            question="What is Python?",
            answer="A programming language.",
            created_at=created,
        )

        assert msg.id == msg_id
        assert msg.user_id == "user-123"
        assert msg.name == "Alice"
        assert msg.question == "What is Python?"
        assert msg.answer == "A programming language."
        assert msg.created_at == created

    def test_default_id_is_generated(self):
        msg = Message(
            user_id="user-1",
            name="Bob",
            question="Q",
            answer="A",
        )

        assert isinstance(msg.id, uuid.UUID)

    def test_default_created_at_is_generated(self):
        before = datetime.now(timezone.utc)
        msg = Message(
            user_id="user-1",
            name="Bob",
            question="Q",
            answer="A",
        )
        after = datetime.now(timezone.utc)

        assert isinstance(msg.created_at, datetime)
        assert before <= msg.created_at <= after

    def test_each_instance_gets_unique_id(self):
        msg1 = Message(user_id="u", name="n", question="q", answer="a")
        msg2 = Message(user_id="u", name="n", question="q", answer="a")

        assert msg1.id != msg2.id

    def test_field_access(self):
        msg = Message(
            user_id="u-test",
            name="TestUser",
            question="Test question?",
            answer="Test answer.",
        )

        # Verify fields are accessible
        assert hasattr(msg, "id")
        assert hasattr(msg, "user_id")
        assert hasattr(msg, "name")
        assert hasattr(msg, "question")
        assert hasattr(msg, "answer")
        assert hasattr(msg, "created_at")
