from __future__ import annotations

from datetime import date

from chat_archive.domain.ports.message_repository import MessageRepository
from chat_archive.infrastructure.timing import log_execution

from .models import GetMessagesByDayResponse, MessageItem


def _extract_context(_self, day: date, page_size: int, page: int) -> dict:
    return {"day": str(day), "page_size": page_size, "page": page}


class GetMessagesByDayUseCase:
    def __init__(self, repo: MessageRepository) -> None:
        self._repo = repo

    @log_execution("use_case.get_messages_by_day", _extract_context)
    async def execute(
        self, day: date, page_size: int, page: int
    ) -> GetMessagesByDayResponse:
        messages, total = await self._repo.find_by_day(day, page_size, page)
        return GetMessagesByDayResponse(
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
