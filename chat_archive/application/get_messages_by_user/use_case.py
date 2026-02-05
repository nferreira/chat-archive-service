from __future__ import annotations

from datetime import date

from chat_archive.domain.ports.message_repository import MessageRepository
from chat_archive.infrastructure.timing import log_execution

from .models import GetMessagesByUserResponse, MessageItem


def _extract_context(
    _self, user_id: str, start: date, end: date, page_size: int, page: int
) -> dict:
    return {"user_id": user_id, "start": str(start), "end": str(end), "page_size": page_size, "page": page}


class GetMessagesByUserUseCase:
    def __init__(self, repo: MessageRepository) -> None:
        self._repo = repo

    @log_execution("use_case.get_messages_by_user", _extract_context)
    async def execute(
        self, user_id: str, start: date, end: date, page_size: int, page: int
    ) -> GetMessagesByUserResponse:
        messages, total = await self._repo.find_by_user(user_id, start, end, page_size, page)
        return GetMessagesByUserResponse(
            items=[
                MessageItem(
                    question=m.question,
                    answer=m.answer,
                    created_at=m.created_at.isoformat(),
                )
                for m in messages
            ],
            total=total,
            page_size=page_size,
            page=page,
        )
