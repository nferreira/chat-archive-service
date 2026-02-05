from __future__ import annotations

from pydantic import BaseModel


class MessageItem(BaseModel):
    question: str
    answer: str
    created_at: str


class GetMessagesByUserResponse(BaseModel):
    items: list[MessageItem]
    total: int
    page_size: int
    page: int
