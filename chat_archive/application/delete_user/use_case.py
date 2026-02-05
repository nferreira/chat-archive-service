from __future__ import annotations

from chat_archive.domain.ports.message_repository import MessageRepository
from chat_archive.infrastructure.timing import log_execution


def _extract_context(_self, user_id: str) -> dict:
    return {}


class DeleteUserUseCase:
    def __init__(self, repo: MessageRepository) -> None:
        self._repo = repo

    @log_execution("use_case.delete_user", _extract_context)
    async def execute(self, user_id: str) -> None:
        await self._repo.delete_by_user(user_id)
