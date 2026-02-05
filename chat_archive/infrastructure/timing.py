"""Timing utilities for measuring operation duration.

This module provides a single-responsibility timing mechanism that can be used
as a context manager or decorator for both sync and async operations.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

import structlog

P = ParamSpec("P")
T = TypeVar("T")

log = structlog.stdlib.get_logger()


@contextmanager
def timed_operation(operation: str, **context: Any):
    """Context manager that measures and logs operation duration.

    Args:
        operation: Name of the operation being timed (e.g., "db.query", "use_case.execute")
        **context: Additional context to include in the log entry

    Yields:
        dict: A mutable dict where 'elapsed_ms' will be set after the block completes.
              Useful if caller needs the timing value.

    Example:
        with timed_operation("db.save", user_id=user_id) as timing:
            await repo.save(entity)
        # timing["elapsed_ms"] contains the duration
    """
    timing: dict[str, Any] = {}
    start = time.perf_counter()
    try:
        yield timing
    finally:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        timing["elapsed_ms"] = elapsed_ms
        log.debug(
            f"{operation}.completed",
            elapsed_ms=elapsed_ms,
            **context,
        )


def log_execution(operation: str, extract_context: Callable[..., dict[str, Any]] | None = None):
    """Decorator that logs execution time for async functions.

    Args:
        operation: Name of the operation (e.g., "use_case.store_message")
        extract_context: Optional callable that extracts log context from function args.
                        Receives (*args, **kwargs) and returns a dict of context values.

    Example:
        @log_execution("use_case.store_message", lambda req: {"user_id": req.user_id})
        async def execute(self, request: StoreMessageRequest) -> StoreMessageResponse:
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            context = extract_context(*args, **kwargs) if extract_context else {}
            log.info(f"{operation}.started", **context)
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                log.info(f"{operation}.completed", elapsed_ms=elapsed_ms, **context)
                return result
            except Exception as e:
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                log.error(
                    f"{operation}.failed",
                    elapsed_ms=elapsed_ms,
                    error=str(e),
                    error_type=type(e).__name__,
                    **context,
                )
                raise

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            context = extract_context(*args, **kwargs) if extract_context else {}
            log.info(f"{operation}.started", **context)
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                log.info(f"{operation}.completed", elapsed_ms=elapsed_ms, **context)
                return result
            except Exception as e:
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                log.error(
                    f"{operation}.failed",
                    elapsed_ms=elapsed_ms,
                    error=str(e),
                    error_type=type(e).__name__,
                    **context,
                )
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator
