"""Tests for timing utilities."""
from __future__ import annotations

import time

import pytest

from chat_archive.infrastructure.timing import log_execution, timed_operation


class TestTimedOperation:
    def test_yields_timing_dict(self):
        with timed_operation("test.op") as timing:
            pass
        assert isinstance(timing, dict)
        assert "elapsed_ms" in timing

    def test_elapsed_ms_is_positive(self):
        with timed_operation("test.op") as timing:
            time.sleep(0.01)  # 10ms
        assert timing["elapsed_ms"] > 0

    def test_elapsed_ms_is_approximately_correct(self):
        with timed_operation("test.op") as timing:
            time.sleep(0.05)  # 50ms
        # Should be at least 40ms but not crazy high
        assert 40 <= timing["elapsed_ms"] <= 200

    def test_accepts_additional_context(self):
        # Should not raise when passed additional kwargs
        with timed_operation("test.op", user_id="u1", extra="data") as timing:
            pass
        assert "elapsed_ms" in timing

    def test_measures_time_even_on_exception(self):
        timing_ref = None
        try:
            with timed_operation("test.op") as timing:
                timing_ref = timing
                raise ValueError("test error")
        except ValueError:
            pass
        assert timing_ref is not None
        assert "elapsed_ms" in timing_ref


class TestLogExecutionDecorator:
    @pytest.mark.asyncio
    async def test_async_function_returns_result(self):
        @log_execution("test.async_op")
        async def async_func(x):
            return x * 2

        result = await async_func(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_async_function_with_context_extractor(self):
        @log_execution("test.async_op", lambda x: {"input": x})
        async def async_func(x):
            return x + 1

        result = await async_func(10)
        assert result == 11

    @pytest.mark.asyncio
    async def test_async_function_propagates_exception(self):
        @log_execution("test.async_op")
        async def async_func():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            await async_func()

    def test_sync_function_returns_result(self):
        @log_execution("test.sync_op")
        def sync_func(x):
            return x * 3

        result = sync_func(4)
        assert result == 12

    def test_sync_function_with_context_extractor(self):
        @log_execution("test.sync_op", lambda x: {"val": x})
        def sync_func(x):
            return x - 1

        result = sync_func(10)
        assert result == 9

    def test_sync_function_propagates_exception(self):
        @log_execution("test.sync_op")
        def sync_func():
            raise RuntimeError("sync error")

        with pytest.raises(RuntimeError, match="sync error"):
            sync_func()

    def test_preserves_function_name(self):
        @log_execution("test.op")
        def my_function():
            pass

        assert my_function.__name__ == "my_function"

    @pytest.mark.asyncio
    async def test_preserves_async_function_name(self):
        @log_execution("test.op")
        async def my_async_function():
            pass

        assert my_async_function.__name__ == "my_async_function"
