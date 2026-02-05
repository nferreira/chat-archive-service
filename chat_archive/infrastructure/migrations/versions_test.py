"""Tests for 001_create_chat_messages migration."""
from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path


def _load_migration_module():
    """Load the migration module using importlib (needed because filename starts with digit)."""
    migration_path = Path(__file__).parent / "versions" / "001_create_chat_messages.py"
    spec = importlib.util.spec_from_file_location("migration_001", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load module once at import time
_migration = _load_migration_module()

PARTITION_START_YEAR = _migration.PARTITION_START_YEAR
PARTITION_START_MONTH = _migration.PARTITION_START_MONTH
PARTITION_END_YEAR = _migration.PARTITION_END_YEAR
PARTITION_END_MONTH = _migration.PARTITION_END_MONTH
_generate_partition_dates = _migration._generate_partition_dates


class TestPartitionConfig:
    def test_partition_start_year(self):
        assert PARTITION_START_YEAR == 2025

    def test_partition_start_month(self):
        assert PARTITION_START_MONTH == 6

    def test_partition_end_year(self):
        assert PARTITION_END_YEAR == 2029

    def test_partition_end_month(self):
        assert PARTITION_END_MONTH == 12


class TestGeneratePartitionDates:
    def test_returns_list(self):
        result = _generate_partition_dates()
        assert isinstance(result, list)

    def test_returns_tuples(self):
        result = _generate_partition_dates()
        assert all(isinstance(item, tuple) for item in result)

    def test_tuple_has_three_elements(self):
        result = _generate_partition_dates()
        assert all(len(item) == 3 for item in result)

    def test_first_element_is_partition_name(self):
        result = _generate_partition_dates()
        first_partition = result[0]
        partition_name, _, _ = first_partition
        assert partition_name == "chat_messages_202506"

    def test_second_element_is_start_date(self):
        result = _generate_partition_dates()
        first_partition = result[0]
        _, start_date, _ = first_partition
        assert start_date == date(2025, 6, 1)

    def test_third_element_is_end_date(self):
        result = _generate_partition_dates()
        first_partition = result[0]
        _, _, end_date = first_partition
        assert end_date == date(2025, 7, 1)

    def test_partition_dates_are_contiguous(self):
        result = _generate_partition_dates()
        for i in range(len(result) - 1):
            _, _, end_date = result[i]
            _, next_start, _ = result[i + 1]
            assert end_date == next_start

    def test_december_partition_ends_in_january(self):
        result = _generate_partition_dates()
        december_partition = next(
            part for part in result if part[0] == "chat_messages_202512"
        )
        _, _, end_date = december_partition
        assert end_date == date(2026, 1, 1)

    def test_last_partition_end_date(self):
        result = _generate_partition_dates()
        _, _, end_date = result[-1]
        assert end_date == date(2030, 1, 1)

    def test_number_of_partitions(self):
        result = _generate_partition_dates()
        expected_count = (2029 - 2025) * 12 + (12 - 6 + 1)
        assert len(result) == expected_count

    def test_partition_names_are_unique(self):
        result = _generate_partition_dates()
        names = [name for name, _, _ in result]
        assert len(names) == len(set(names))

    def test_partition_ranges_do_not_overlap(self):
        result = _generate_partition_dates()
        for i in range(len(result) - 1):
            _, start_date, end_date = result[i]
            _, next_start, _ = result[i + 1]
            assert end_date <= next_start

    def test_partition_names_format(self):
        result = _generate_partition_dates()
        for name, _, _ in result:
            assert name.startswith("chat_messages_")
            assert len(name) == len("chat_messages_YYYYMM")
