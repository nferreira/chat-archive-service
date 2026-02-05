from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Text, Uuid, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ChatMessageRow(Base):
    """ORM model for chat messages (partitioned by created_at).

    The table uses PostgreSQL monthly partitioning on created_at.
    Primary key is composite (id, created_at) as required for partitioning.

    Indexes (with DESC ordering for efficient LIMIT queries):
    - ix_chat_messages_user_created: (user_id, created_at DESC, id DESC)
      For find_by_user and delete_by_user queries
    - ix_chat_messages_created: (created_at DESC, id DESC)
      For find_by_day and find_by_period queries
    """

    __tablename__ = "chat_messages"

    # Composite primary key required for partitioning (partition key must be included)
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
        server_default=text("now()"),
    )
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("ix_chat_messages_user_created", "user_id", created_at.desc(), id.desc()),
        Index("ix_chat_messages_created", created_at.desc(), id.desc()),
    )
