"""create chat_messages table with monthly partitioning

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

Monthly partitioning chosen over daily to:
1. Reduce partition overhead when querying long date ranges
2. Enable better LIMIT optimization with fewer partitions to scan
3. Improve query planning time (fewer partitions = faster planning)

"""
from datetime import date
from typing import Sequence, Union

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Partition configuration
PARTITION_START_YEAR = 2025
PARTITION_START_MONTH = 6
PARTITION_END_YEAR = 2029
PARTITION_END_MONTH = 12


def _generate_partition_dates() -> list[tuple[str, date, date]]:
    """Generate monthly partition date ranges for the configured period."""
    partitions = []
    year = PARTITION_START_YEAR
    month = PARTITION_START_MONTH

    while year < PARTITION_END_YEAR or (year == PARTITION_END_YEAR and month <= PARTITION_END_MONTH):
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        partition_name = f"chat_messages_{year}{month:02d}"
        partitions.append((partition_name, start_date, end_date))

        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    return partitions


def upgrade() -> None:
    # Create the partitioned parent table
    # Note: Primary key must include the partition key (created_at)
    # question and answer use TEXT type which supports unlimited length (up to 1GB)
    op.execute("""
        CREATE TABLE chat_messages (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
    """)

    # Create monthly partitions
    # Partition naming: chat_messages_YYYYMM
    for partition_name, start_date, end_date in _generate_partition_dates():
        op.execute(f"""
            CREATE TABLE {partition_name} PARTITION OF chat_messages
            FOR VALUES FROM ('{start_date.isoformat()}') TO ('{end_date.isoformat()}')
        """)

    # Create a default partition for any data outside the defined ranges
    op.execute("""
        CREATE TABLE chat_messages_default PARTITION OF chat_messages DEFAULT
    """)

    # Index strategy based on query patterns:
    # Indexes on partitioned tables are automatically created on all partitions
    #
    # 1. ix_chat_messages_user_created: Composite index for find_by_user queries
    #    - Filters by user_id, orders by created_at DESC, id DESC
    #    - Also serves delete_by_user (leading column is user_id)
    #
    # 2. ix_chat_messages_created: For find_by_day and find_by_period queries
    #    - Range queries on created_at with ORDER BY created_at DESC, id DESC

    op.execute("""
        CREATE INDEX ix_chat_messages_user_created
        ON chat_messages (user_id, created_at DESC, id DESC)
    """)
    op.execute("""
        CREATE INDEX ix_chat_messages_created
        ON chat_messages (created_at DESC, id DESC)
    """)


def downgrade() -> None:
    # Dropping the parent table cascades to all partitions
    op.execute("DROP TABLE IF EXISTS chat_messages CASCADE")
