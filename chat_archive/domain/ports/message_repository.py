from __future__ import annotations

import abc
from datetime import date

from chat_archive.domain.models.message import Message


class MessageRepository(abc.ABC):
    @abc.abstractmethod
    async def save(self, message: Message) -> Message: ...

    @abc.abstractmethod
    async def find_by_user(
        self, user_id: str, start: date, end: date, page_size: int, page: int
    ) -> tuple[list[Message], int]: ...

    @abc.abstractmethod
    async def find_by_day(
        self, day: date, page_size: int, page: int
    ) -> tuple[list[Message], int]: ...

    @abc.abstractmethod
    async def find_by_period(
        self, start: date, end: date, page_size: int, page: int
    ) -> tuple[list[Message], int]: ...

    @abc.abstractmethod
    async def delete_by_user(self, user_id: str) -> None: ...
