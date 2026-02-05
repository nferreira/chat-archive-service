from __future__ import annotations

from chat_archive.domain.models.message import Message
from chat_archive.domain.ports.message_repository import MessageRepository
from chat_archive.infrastructure.timing import log_execution

from .models import StoreMessageRequest, StoreMessageResponse


def _extract_store_context(_self, request: StoreMessageRequest) -> dict:
    return {}


class StoreMessageUseCase:
    def __init__(self, repo: MessageRepository) -> None:
        self._repo = repo

    @log_execution("use_case.store_message", _extract_store_context)
    async def execute(self, request: StoreMessageRequest) -> StoreMessageResponse:
        message = Message(
            user_id=request.user_id,
            name=request.name,
            question=request.question,
            answer=request.answer,
        )
        saved = await self._repo.save(message)
        return StoreMessageResponse(
            id=saved.id,
            created_at=saved.created_at.isoformat(),
        )
