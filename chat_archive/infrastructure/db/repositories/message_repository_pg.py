from __future__ import annotations

from datetime import date, datetime, timezone

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chat_archive.domain.models.message import Message
from chat_archive.domain.ports.message_repository import MessageRepository
from chat_archive.infrastructure.db.orm import ChatMessageRow
from chat_archive.infrastructure.timing import timed_operation

log = structlog.stdlib.get_logger()


class PostgresMessageRepository(MessageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, message: Message) -> Message:
        with timed_operation("db.save", message_id=str(message.id)):
            row = ChatMessageRow(
                id=message.id,
                user_id=message.user_id,
                name=message.name,
                question=message.question,
                answer=message.answer,
                created_at=message.created_at,
            )
            self._session.add(row)
            await self._session.flush()
        return message

    async def find_by_user(
        self, user_id: str, start: date, end: date, page_size: int, page: int
    ) -> tuple[list[Message], int]:
        skip = page * page_size
        with timed_operation(
            "db.find_by_user",
            user_id=user_id,
            start=str(start),
            end=str(end),
            page_size=page_size,
            page=page,
        ) as timing:
            start_dt = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
            end_dt = datetime(end.year, end.month, end.day, 23, 59, 59, 999999, tzinfo=timezone.utc)

            base = select(ChatMessageRow).where(
                ChatMessageRow.user_id == user_id,
                ChatMessageRow.created_at >= start_dt,
                ChatMessageRow.created_at <= end_dt,
            )
            count_q = select(func.count()).select_from(base.subquery())
            total = (await self._session.execute(count_q)).scalar_one()

            rows_q = base.order_by(
                ChatMessageRow.created_at.desc(), ChatMessageRow.id.desc()
            ).limit(page_size).offset(skip)
            rows = (await self._session.execute(rows_q)).scalars().all()
            results = [self._to_domain(r) for r in rows]

        log.debug(
            "db.find_by_user.results",
            user_id=user_id,
            start=str(start),
            end=str(end),
            total=total,
            returned=len(results),
            elapsed_ms=timing.get("elapsed_ms"),
        )
        return results, total

    async def find_by_day(
        self, day: date, page_size: int, page: int
    ) -> tuple[list[Message], int]:
        skip = page * page_size
        with timed_operation("db.find_by_day", day=str(day), page_size=page_size, page=page) as timing:
            start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
            end = datetime(day.year, day.month, day.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
            results, total = await self._find_in_range(start, end, page_size, skip)

        log.debug(
            "db.find_by_day.results",
            day=str(day),
            total=total,
            returned=len(results),
            elapsed_ms=timing.get("elapsed_ms"),
        )
        return results, total

    async def find_by_period(
        self, start: date, end: date, page_size: int, page: int
    ) -> tuple[list[Message], int]:
        skip = page * page_size
        with timed_operation("db.find_by_period", start=str(start), end=str(end), page_size=page_size, page=page) as timing:
            start_dt = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
            end_dt = datetime(end.year, end.month, end.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
            results, total = await self._find_in_range(start_dt, end_dt, page_size, skip)

        log.debug(
            "db.find_by_period.results",
            start=str(start),
            end=str(end),
            total=total,
            returned=len(results),
            elapsed_ms=timing.get("elapsed_ms"),
        )
        return results, total

    async def delete_by_user(self, user_id: str) -> None:
        with timed_operation("db.delete_by_user"):
            stmt = delete(ChatMessageRow).where(ChatMessageRow.user_id == user_id)
            result = await self._session.execute(stmt)
            await self._session.flush()
            log.debug("db.delete_by_user.result", rows_deleted=result.rowcount)

    async def _find_in_range(
        self, start: datetime, end: datetime, page_size: int, skip: int
    ) -> tuple[list[Message], int]:
        base = select(ChatMessageRow).where(
            ChatMessageRow.created_at >= start,
            ChatMessageRow.created_at <= end,
        )
        count_q = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        rows_q = base.order_by(
            ChatMessageRow.created_at.desc(), ChatMessageRow.id.desc()
        ).limit(page_size).offset(skip)
        rows = (await self._session.execute(rows_q)).scalars().all()
        return [self._to_domain(r) for r in rows], total

    @staticmethod
    def _to_domain(row: ChatMessageRow) -> Message:
        return Message(
            id=row.id,
            user_id=row.user_id,
            name=row.name,
            question=row.question,
            answer=row.answer,
            created_at=row.created_at,
        )
