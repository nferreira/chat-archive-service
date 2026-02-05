from __future__ import annotations

from datetime import date

from chat_archive.domain.ports.message_repository import MessageRepository
from chat_archive.infrastructure.timing import log_execution

from .models import GetMessagesByPeriodResponse, MessageItem


def _extract_context(_self, start: date, end: date, page_size: int, page: int) -> dict:
    return {"start": str(start), "end": str(end), "page_size": page_size, "page": page}


class GetMessagesByPeriodUseCase:
    def __init__(self, repo: MessageRepository) -> None:
        self._repo = repo

    @log_execution("use_case.get_messages_by_period", _extract_context)
    async def execute(
        self, start: date, end: date, page_size: int, page: int
    ) -> GetMessagesByPeriodResponse:
        messages, total = await self._repo.find_by_period(start, end, page_size, page)
        return GetMessagesByPeriodResponse(
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
