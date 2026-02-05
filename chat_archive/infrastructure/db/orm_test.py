"""Tests for ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import inspect

from chat_archive.infrastructure.db.orm import Base, ChatMessageRow


class TestChatMessageRowModel:
    def test_table_name(self):
        assert ChatMessageRow.__tablename__ == "chat_messages"

    def test_inherits_from_base(self):
        assert issubclass(ChatMessageRow, Base)

    def test_has_id_column(self):
        mapper = inspect(ChatMessageRow)
        columns = [c.key for c in mapper.columns]
        assert "id" in columns

    def test_has_user_id_column(self):
        mapper = inspect(ChatMessageRow)
        columns = [c.key for c in mapper.columns]
        assert "user_id" in columns

    def test_has_name_column(self):
        mapper = inspect(ChatMessageRow)
        columns = [c.key for c in mapper.columns]
        assert "name" in columns

    def test_has_question_column(self):
        mapper = inspect(ChatMessageRow)
        columns = [c.key for c in mapper.columns]
        assert "question" in columns

    def test_has_answer_column(self):
        mapper = inspect(ChatMessageRow)
        columns = [c.key for c in mapper.columns]
        assert "answer" in columns

    def test_has_created_at_column(self):
        mapper = inspect(ChatMessageRow)
        columns = [c.key for c in mapper.columns]
        assert "created_at" in columns

    def test_primary_key_includes_id(self):
        mapper = inspect(ChatMessageRow)
        pk_columns = [c.name for c in mapper.primary_key]
        assert "id" in pk_columns

    def test_primary_key_includes_created_at(self):
        # Composite PK for partitioning
        mapper = inspect(ChatMessageRow)
        pk_columns = [c.name for c in mapper.primary_key]
        assert "created_at" in pk_columns

    def test_has_user_created_index(self):
        indexes = ChatMessageRow.__table__.indexes
        index_names = [idx.name for idx in indexes]
        assert "ix_chat_messages_user_created" in index_names

    def test_has_created_index(self):
        indexes = ChatMessageRow.__table__.indexes
        index_names = [idx.name for idx in indexes]
        assert "ix_chat_messages_created" in index_names

    def test_can_instantiate_row(self):
        row = ChatMessageRow(
            id=uuid.uuid4(),
            user_id="user-1",
            name="Alice",
            question="Q?",
            answer="A.",
            created_at=datetime.now(timezone.utc),
        )
        assert row.user_id == "user-1"
        assert row.name == "Alice"
        assert row.question == "Q?"
        assert row.answer == "A."
