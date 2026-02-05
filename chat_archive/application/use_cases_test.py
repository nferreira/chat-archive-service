from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest

from chat_archive.application.delete_user.use_case import DeleteUserUseCase
from chat_archive.application.get_messages_by_day.use_case import GetMessagesByDayUseCase
from chat_archive.application.get_messages_by_period.use_case import GetMessagesByPeriodUseCase
from chat_archive.application.get_messages_by_user.use_case import GetMessagesByUserUseCase
from chat_archive.application.store_message.models import StoreMessageRequest
from chat_archive.application.store_message.use_case import StoreMessageUseCase
from chat_archive.domain.models.message import Message


def _make_message(**overrides) -> Message:
    defaults = dict(
        id=uuid.uuid4(),
        user_id="user-1",
        name="Alice",
        question="What is Python?",
        answer="A programming language.",
        created_at=datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return Message(**defaults)


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    return repo


class TestStoreMessage:
    @pytest.mark.asyncio
    async def test_creates_and_saves_message(self, mock_repo):
        async def save_side_effect(msg):
            return msg

        mock_repo.save.side_effect = save_side_effect
        uc = StoreMessageUseCase(mock_repo)

        req = StoreMessageRequest(
            user_id="user-1", name="Alice", question="Hi?", answer="Hello!"
        )
        result = await uc.execute(req)

        mock_repo.save.assert_called_once()
        assert result.id is not None
        assert result.created_at is not None

    @pytest.mark.asyncio
    async def test_response_has_iso_created_at(self, mock_repo):
        mock_repo.save.side_effect = lambda msg: msg
        uc = StoreMessageUseCase(mock_repo)

        req = StoreMessageRequest(
            user_id="u1", name="Bob", question="Q", answer="A"
        )
        result = await uc.execute(req)
        # Should be parseable as ISO 8601
        datetime.fromisoformat(result.created_at)


class TestGetMessagesByUser:
    @pytest.mark.asyncio
    async def test_returns_paginated_items(self, mock_repo):
        messages = [_make_message(), _make_message()]
        mock_repo.find_by_user.return_value = (messages, 2)

        uc = GetMessagesByUserUseCase(mock_repo)
        result = await uc.execute(
            "user-1", start=date(2025, 6, 1), end=date(2025, 6, 30), page_size=50, page=0
        )

        assert result.total == 2
        assert result.page_size == 50
        assert result.page == 0
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_items_have_no_user_id_or_name(self, mock_repo):
        mock_repo.find_by_user.return_value = ([_make_message()], 1)

        uc = GetMessagesByUserUseCase(mock_repo)
        result = await uc.execute(
            "user-1", start=date(2025, 6, 1), end=date(2025, 6, 30), page_size=50, page=0
        )

        item_dict = result.items[0].model_dump()
        assert "user_id" not in item_dict
        assert "name" not in item_dict
        assert "question" in item_dict
        assert "answer" in item_dict
        assert "created_at" in item_dict


class TestGetMessagesByDay:
    @pytest.mark.asyncio
    async def test_returns_paginated(self, mock_repo):
        mock_repo.find_by_day.return_value = ([_make_message()], 1)

        uc = GetMessagesByDayUseCase(mock_repo)
        result = await uc.execute(date(2025, 6, 15), page_size=50, page=0)

        assert result.total == 1
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_items_privacy(self, mock_repo):
        mock_repo.find_by_day.return_value = ([_make_message()], 1)

        uc = GetMessagesByDayUseCase(mock_repo)
        result = await uc.execute(date(2025, 6, 15), page_size=50, page=0)

        item_dict = result.items[0].model_dump()
        assert "user_id" not in item_dict
        assert "name" not in item_dict


class TestGetMessagesByPeriod:
    @pytest.mark.asyncio
    async def test_returns_paginated(self, mock_repo):
        mock_repo.find_by_period.return_value = ([_make_message()], 1)

        uc = GetMessagesByPeriodUseCase(mock_repo)
        result = await uc.execute(
            date(2025, 6, 1), date(2025, 6, 30), page_size=50, page=0
        )

        assert result.total == 1
        assert len(result.items) == 1


class TestDeleteUser:
    @pytest.mark.asyncio
    async def test_calls_delete_by_user(self, mock_repo):
        mock_repo.delete_by_user.return_value = None

        uc = DeleteUserUseCase(mock_repo)
        await uc.execute("user-1")

        mock_repo.delete_by_user.assert_called_once_with("user-1")
