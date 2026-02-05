from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class StoreMessageRequest(BaseModel):
    user_id: str
    name: str
    question: str
    answer: str


class StoreMessageResponse(BaseModel):
    id: uuid.UUID
    created_at: str
