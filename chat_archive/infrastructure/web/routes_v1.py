from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from chat_archive.application.delete_user.use_case import DeleteUserUseCase
from chat_archive.application.get_messages_by_day.models import GetMessagesByDayResponse
from chat_archive.application.get_messages_by_day.use_case import GetMessagesByDayUseCase
from chat_archive.application.get_messages_by_period.models import GetMessagesByPeriodResponse
from chat_archive.application.get_messages_by_period.use_case import GetMessagesByPeriodUseCase
from chat_archive.application.get_messages_by_user.models import GetMessagesByUserResponse
from chat_archive.application.get_messages_by_user.use_case import GetMessagesByUserUseCase
from chat_archive.application.store_message.models import StoreMessageRequest, StoreMessageResponse
from chat_archive.application.store_message.use_case import StoreMessageUseCase
from chat_archive.container import (
    get_delete_user_use_case,
    get_message_repository,
    get_messages_by_user_use_case,
    get_session,
    get_store_message_use_case,
)
from chat_archive.infrastructure.db.repositories.message_repository_pg import PostgresMessageRepository

router = APIRouter(prefix="/api/v1")


def _paginated_response(result: BaseModel) -> Response | Any:
    """Return 204 with pagination headers if no items, otherwise return the result."""
    if not result.items:
        return Response(
            status_code=204,
            headers={
                "X-Total-Count": str(result.total),
                "X-Page-Size": str(result.page_size),
                "X-Page": str(result.page),
            },
        )
    return result


@router.post(
    "/messages",
    status_code=201,
    tags=["messages"],
    summary="Store a chat message",
    description="Archive a new chat message with user information, question, and answer.",
    response_model=StoreMessageResponse,
    responses={
        201: {
            "description": "Message stored successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "created_at": "2025-06-15T12:00:00Z"
                    }
                }
            }
        },
        422: {"description": "Validation error - missing or invalid fields"},
    },
)
async def store_message(
    body: StoreMessageRequest,
    session: AsyncSession = Depends(get_session),
    uc: StoreMessageUseCase = Depends(get_store_message_use_case),
):
    result = await uc.execute(body)
    await session.commit()
    return result


@router.get(
    "/messages",
    tags=["messages"],
    summary="Query messages by day or period",
    description="""
Retrieve chat messages filtered by either a specific day or a date range.

**Query modes:**
- **By day**: Provide `day` parameter to get all messages for that specific day
- **By period**: Provide both `start` and `end` parameters to get messages in that range

**Privacy:** Response excludes `user_id` and `name` fields for privacy protection.

**Pagination:** Use `page_size` and `page` parameters. Returns 204 No Content with
pagination headers (`X-Total-Count`, `X-Page-Size`, `X-Page`) when no results found.
    """,
    response_model=GetMessagesByDayResponse | GetMessagesByPeriodResponse,
    responses={
        200: {"description": "Messages found"},
        204: {
            "description": "No messages found",
            "headers": {
                "X-Total-Count": {"description": "Total number of matching messages", "schema": {"type": "integer"}},
                "X-Page-Size": {"description": "Requested page size", "schema": {"type": "integer"}},
                "X-Page": {"description": "Current page number", "schema": {"type": "integer"}},
            },
        },
        422: {"description": "Validation error - invalid parameters or parameter combination"},
    },
)
async def get_messages(
    day: date | None = Query(
        default=None,
        description="Filter by specific day (cannot combine with start/end)",
    ),
    start: date | None = Query(
        default=None,
        description="Start date for period filter (inclusive, requires end)",
    ),
    end: date | None = Query(
        default=None,
        description="End date for period filter (inclusive, requires start)",
    ),
    page_size: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Number of items per page",
    ),
    page: int = Query(
        default=0,
        ge=0,
        description="Page number (0-indexed)",
    ),
    repo: PostgresMessageRepository = Depends(get_message_repository),
):
    if day is not None:
        if start is not None or end is not None:
            raise HTTPException(
                status_code=422,
                detail="Cannot combine 'day' with 'start'/'end' parameters.",
            )
        uc = GetMessagesByDayUseCase(repo)
        result = await uc.execute(day, page_size, page)
        return _paginated_response(result)

    if start is not None and end is not None:
        uc = GetMessagesByPeriodUseCase(repo)
        result = await uc.execute(start, end, page_size, page)
        return _paginated_response(result)

    if start is not None or end is not None:
        raise HTTPException(
            status_code=422,
            detail="Both 'start' and 'end' are required for period filtering.",
        )

    raise HTTPException(
        status_code=422,
        detail="Provide either 'day' or both 'start' and 'end' query parameters.",
    )


@router.get(
    "/users/{user_id}/messages",
    tags=["users"],
    summary="Get messages for a specific user",
    description="""
Retrieve all chat messages for a specific user within a date range.

**Privacy:** Response excludes `user_id` and `name` fields for privacy protection.
Only the question, answer, and timestamp are returned.

**Pagination:** Use `page_size` and `page` parameters. Returns 204 No Content with
pagination headers when no results found.
    """,
    response_model=GetMessagesByUserResponse,
    responses={
        200: {"description": "Messages found"},
        204: {
            "description": "No messages found for this user in the specified range",
            "headers": {
                "X-Total-Count": {"description": "Total number of matching messages", "schema": {"type": "integer"}},
                "X-Page-Size": {"description": "Requested page size", "schema": {"type": "integer"}},
                "X-Page": {"description": "Current page number", "schema": {"type": "integer"}},
            },
        },
        422: {"description": "Validation error - missing or invalid parameters"},
    },
)
async def get_messages_by_user(
    user_id: str = Path(..., description="The unique identifier of the user"),
    start: date = Query(
        ...,
        description="Start date (inclusive)",
    ),
    end: date = Query(
        ...,
        description="End date (inclusive)",
    ),
    page_size: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Number of items per page",
    ),
    page: int = Query(
        default=0,
        ge=0,
        description="Page number (0-indexed)",
    ),
    uc: GetMessagesByUserUseCase = Depends(get_messages_by_user_use_case),
):
    result = await uc.execute(user_id, start, end, page_size, page)
    return _paginated_response(result)


@router.delete(
    "/users/{user_id}",
    status_code=204,
    tags=["users"],
    summary="Delete all data for a user",
    description="""
Delete all chat messages associated with a specific user.

This endpoint supports GDPR right-to-erasure requests by permanently removing
all messages for the specified user.

**Warning:** This operation is irreversible.
    """,
    responses={
        204: {"description": "User data deleted successfully"},
    },
)
async def delete_user(
    user_id: str = Path(..., description="The unique identifier of the user to delete"),
    session: AsyncSession = Depends(get_session),
    uc: DeleteUserUseCase = Depends(get_delete_user_use_case),
):
    await uc.execute(user_id)
    await session.commit()
    return Response(status_code=204)
