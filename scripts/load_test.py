#!/usr/bin/env python3
"""Load test script for chat archive APIs.

Generates messages with different users and content across a date range,
then stress tests the read APIs.

Usage:
    # Seed database with test data
    python scripts/load_test.py seed --count 10000

    # Run read API load test
    python scripts/load_test.py read --concurrency 10 --duration 60

    # Run full load test (seed + read)
    python scripts/load_test.py full --seed-count 5000 --concurrency 10 --duration 30
"""

from __future__ import annotations

import argparse
import asyncio
import random
import string
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

# Configuration
DEFAULT_BASE_URL = "http://localhost:8000"
DATE_START = date(2026, 2, 1)
DATE_END = date(2026, 2, 28)

# Sample data for generating realistic content
FIRST_NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry",
    "Ivy", "Jack", "Kate", "Leo", "Mia", "Noah", "Olivia", "Paul",
    "Quinn", "Rose", "Sam", "Tara", "Uma", "Victor", "Wendy", "Xavier",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
]

QUESTION_TEMPLATES = [
    "How do I {action} in {technology}?",
    "What is the best way to {action}?",
    "Can you explain {concept} to me?",
    "Why does {technology} {behavior}?",
    "How can I improve {aspect} of my {thing}?",
    "What are the differences between {thing1} and {thing2}?",
    "Is it possible to {action} with {technology}?",
    "What should I consider when {action}?",
    "How do I troubleshoot {problem}?",
    "What are best practices for {concept}?",
]

ACTIONS = [
    "implement authentication", "optimize performance", "handle errors",
    "write tests", "deploy", "scale", "refactor", "debug", "monitor",
    "configure", "integrate", "migrate", "backup", "secure", "automate",
]

TECHNOLOGIES = [
    "Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis",
    "SQLAlchemy", "asyncio", "pytest", "Git", "AWS", "React", "TypeScript",
]

CONCEPTS = [
    "dependency injection", "SOLID principles", "microservices", "REST APIs",
    "database indexing", "caching strategies", "async programming",
    "event-driven architecture", "CI/CD pipelines", "containerization",
]

ANSWER_TEMPLATES = [
    "To {action}, you should first {step1}, then {step2}. This approach ensures {benefit}.",
    "The key to {concept} is understanding that {explanation}. Here's an example: {example}.",
    "{technology} handles this by {mechanism}. You can configure it using {method}.",
    "There are several approaches: 1) {approach1}, 2) {approach2}. I recommend {recommendation}.",
    "This is a common question. The solution involves {solution}. Make sure to {warning}.",
]


def generate_user_id() -> str:
    """Generate a random user ID."""
    return f"user_{uuid.uuid4().hex[:8]}"


def generate_name() -> str:
    """Generate a random full name."""
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def generate_question() -> str:
    """Generate a random question."""
    template = random.choice(QUESTION_TEMPLATES)
    return template.format(
        action=random.choice(ACTIONS),
        technology=random.choice(TECHNOLOGIES),
        concept=random.choice(CONCEPTS),
        behavior="behave this way",
        aspect="the performance",
        thing=random.choice(TECHNOLOGIES),
        thing1=random.choice(TECHNOLOGIES),
        thing2=random.choice(TECHNOLOGIES),
        problem="this issue",
    )


def generate_answer() -> str:
    """Generate a random answer."""
    template = random.choice(ANSWER_TEMPLATES)
    return template.format(
        action=random.choice(ACTIONS),
        step1="understand the requirements",
        step2="implement the solution incrementally",
        benefit="maintainability and reliability",
        concept=random.choice(CONCEPTS),
        explanation="it separates concerns effectively",
        example="see the documentation for details",
        technology=random.choice(TECHNOLOGIES),
        mechanism="internal optimization",
        method="configuration files or environment variables",
        approach1="use the built-in features",
        approach2="implement a custom solution",
        recommendation="starting with the simpler option",
        solution="careful analysis and systematic debugging",
        warning="test thoroughly before deploying",
    )


def generate_random_datetime(start: date, end: date) -> datetime:
    """Generate a random datetime within the date range."""
    days_between = (end - start).days
    random_days = random.randint(0, days_between)
    random_date = start + timedelta(days=random_days)
    random_time = timedelta(
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return datetime.combine(random_date, datetime.min.time(), tzinfo=timezone.utc) + random_time


@dataclass
class LoadTestStats:
    """Statistics for load test results."""

    requests: int = 0
    successes: int = 0
    failures: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float("inf")
    max_time_ms: float = 0.0
    status_codes: dict[int, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def record(self, elapsed_ms: float, status_code: int | None, error: str | None = None) -> None:
        self.requests += 1
        self.total_time_ms += elapsed_ms
        self.min_time_ms = min(self.min_time_ms, elapsed_ms)
        self.max_time_ms = max(self.max_time_ms, elapsed_ms)

        if status_code:
            self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
            if 200 <= status_code < 300:
                self.successes += 1
            else:
                self.failures += 1
        else:
            self.failures += 1

        if error:
            if len(self.errors) < 10:  # Keep only first 10 errors
                self.errors.append(error)

    @property
    def avg_time_ms(self) -> float:
        return self.total_time_ms / self.requests if self.requests > 0 else 0.0

    def __str__(self) -> str:
        lines = [
            f"Total requests:  {self.requests}",
            f"Successes:       {self.successes}",
            f"Failures:        {self.failures}",
            f"Avg time:        {self.avg_time_ms:.2f} ms",
            f"Min time:        {self.min_time_ms:.2f} ms" if self.min_time_ms != float("inf") else "Min time:        N/A",
            f"Max time:        {self.max_time_ms:.2f} ms",
            f"Status codes:    {dict(sorted(self.status_codes.items()))}",
        ]
        if self.errors:
            lines.append(f"Sample errors:   {self.errors[:3]}")
        return "\n".join(lines)


class LoadTester:
    """Load tester for chat archive APIs."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.users: list[str] = []
        self.dates: list[date] = []

    async def seed_database(self, count: int, batch_size: int = 100) -> None:
        """Seed the database with test messages."""
        print(f"Seeding database with {count} messages...")
        print(f"Date range: {DATE_START} to {DATE_END}")

        # Generate a pool of users (reuse users for realistic distribution)
        num_users = max(10, count // 50)  # ~50 messages per user on average
        self.users = [generate_user_id() for _ in range(num_users)]
        print(f"Generated {num_users} unique users")

        # Generate dates for later querying
        self.dates = []
        current = DATE_START
        while current <= DATE_END:
            self.dates.append(current)
            current += timedelta(days=1)

        # We need to insert directly into database since API uses now() for created_at
        # Import here to avoid dependency issues when just running read tests
        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine

            from chat_archive.infrastructure.db.engine import DATABASE_URL
        except ImportError as e:
            print(f"Error: Could not import required modules: {e}")
            print("Make sure you're running from the project root with dependencies installed.")
            sys.exit(1)

        engine = create_async_engine(DATABASE_URL)

        inserted = 0
        start_time = time.perf_counter()

        async with engine.begin() as conn:
            for batch_start in range(0, count, batch_size):
                batch_end = min(batch_start + batch_size, count)
                values = []

                for _ in range(batch_end - batch_start):
                    user_id = random.choice(self.users)
                    name = generate_name()
                    question = generate_question()
                    answer = generate_answer()
                    created_at = generate_random_datetime(DATE_START, DATE_END)

                    values.append({
                        "user_id": user_id,
                        "name": name,
                        "question": question,
                        "answer": answer,
                        "created_at": created_at,
                    })

                # Batch insert
                await conn.execute(
                    text("""
                        INSERT INTO chat_messages (user_id, name, question, answer, created_at)
                        VALUES (:user_id, :name, :question, :answer, :created_at)
                    """),
                    values,
                )

                inserted += len(values)
                elapsed = time.perf_counter() - start_time
                rate = inserted / elapsed if elapsed > 0 else 0
                print(f"  Inserted {inserted}/{count} messages ({rate:.0f}/sec)", end="\r")

        await engine.dispose()

        elapsed = time.perf_counter() - start_time
        print(f"\nSeeding complete: {inserted} messages in {elapsed:.2f}s ({inserted/elapsed:.0f}/sec)")

    async def run_read_load_test(
        self,
        concurrency: int,
        duration_seconds: int,
    ) -> dict[str, LoadTestStats]:
        """Run load test against read APIs."""
        print(f"Running read load test: concurrency={concurrency}, duration={duration_seconds}s")

        # Get some users and dates from the database for querying
        await self._fetch_test_data()

        if not self.users:
            print("Warning: No users found in database. Run 'seed' first.")
            return {}

        stats: dict[str, LoadTestStats] = {
            "get_by_user": LoadTestStats(),
            "get_by_day": LoadTestStats(),
            "get_by_period": LoadTestStats(),
        }

        stop_event = asyncio.Event()

        async def worker(worker_id: int) -> None:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
                while not stop_event.is_set():
                    # Randomly choose an endpoint
                    endpoint = random.choice(["get_by_user", "get_by_day", "get_by_period"])

                    try:
                        start = time.perf_counter()

                        if endpoint == "get_by_user":
                            user_id = random.choice(self.users)
                            # Random date range within available dates
                            start_idx = random.randint(0, max(0, len(self.dates) - 30))
                            period_start = self.dates[start_idx]
                            period_end = self.dates[min(start_idx + random.randint(7, 30), len(self.dates) - 1)]
                            page_size = random.choice([10, 50, 100])
                            page = random.randint(0, 5)
                            response = await client.get(
                                f"/api/v1/users/{user_id}/messages",
                                params={
                                    "start": period_start.isoformat(),
                                    "end": period_end.isoformat(),
                                    "page_size": page_size,
                                    "page": page,
                                },
                            )

                        elif endpoint == "get_by_day":
                            day = random.choice(self.dates)
                            page_size = random.choice([10, 50, 100])
                            page = random.randint(0, 5)
                            response = await client.get(
                                "/api/v1/messages",
                                params={"day": day.isoformat(), "page_size": page_size, "page": page},
                            )

                        else:  # get_by_period
                            start_idx = random.randint(0, len(self.dates) - 30)
                            period_start = self.dates[start_idx]
                            period_end = self.dates[min(start_idx + random.randint(7, 30), len(self.dates) - 1)]
                            page_size = random.choice([10, 50, 100])
                            page = random.randint(0, 5)
                            response = await client.get(
                                "/api/v1/messages",
                                params={
                                    "start": period_start.isoformat(),
                                    "end": period_end.isoformat(),
                                    "page_size": page_size,
                                    "page": page,
                                },
                            )

                        elapsed_ms = (time.perf_counter() - start) * 1000
                        stats[endpoint].record(elapsed_ms, response.status_code)

                    except Exception as e:
                        elapsed_ms = (time.perf_counter() - start) * 1000
                        stats[endpoint].record(elapsed_ms, None, str(e))

        # Start workers
        workers = [asyncio.create_task(worker(i)) for i in range(concurrency)]

        # Run for specified duration
        print(f"Load test running for {duration_seconds} seconds...")
        await asyncio.sleep(duration_seconds)
        stop_event.set()

        # Wait for workers to finish
        await asyncio.gather(*workers, return_exceptions=True)

        # Print results
        print("\n" + "=" * 60)
        print("LOAD TEST RESULTS")
        print("=" * 60)

        total_requests = sum(s.requests for s in stats.values())
        total_successes = sum(s.successes for s in stats.values())
        total_failures = sum(s.failures for s in stats.values())

        print(f"\nOverall: {total_requests} requests, {total_successes} successes, {total_failures} failures")
        print(f"Throughput: {total_requests / duration_seconds:.2f} req/sec")

        for endpoint, endpoint_stats in stats.items():
            print(f"\n{endpoint}:")
            print("-" * 40)
            print(endpoint_stats)

        return stats

    async def _fetch_test_data(self) -> None:
        """Fetch existing users and dates from database for querying."""
        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine

            from chat_archive.infrastructure.db.engine import DATABASE_URL
        except ImportError:
            # Fall back to API if direct DB access not available
            return

        engine = create_async_engine(DATABASE_URL)

        async with engine.begin() as conn:
            # Get unique users
            result = await conn.execute(
                text("SELECT DISTINCT user_id FROM chat_messages LIMIT 1000")
            )
            self.users = [row[0] for row in result.fetchall()]

            # Get date range from actual data
            result = await conn.execute(
                text("SELECT MIN(created_at::date), MAX(created_at::date) FROM chat_messages")
            )
            row = result.fetchone()
            if row and row[0] and row[1]:
                self.dates = []
                current = row[0]
                while current <= row[1]:
                    self.dates.append(current)
                    current += timedelta(days=1)

        await engine.dispose()

        print(f"Found {len(self.users)} unique users and {len(self.dates)} days of data")

    async def run_write_load_test(
        self,
        concurrency: int,
        duration_seconds: int,
    ) -> LoadTestStats:
        """Run load test against write API (store message)."""
        print(f"Running write load test: concurrency={concurrency}, duration={duration_seconds}s")

        stats = LoadTestStats()
        stop_event = asyncio.Event()

        async def worker(worker_id: int) -> None:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
                while not stop_event.is_set():
                    try:
                        start = time.perf_counter()

                        user_id = generate_user_id()
                        response = await client.post(
                            f"/api/v1/users/{user_id}/messages",
                            json={
                                "name": generate_name(),
                                "question": generate_question(),
                                "answer": generate_answer(),
                            },
                        )

                        elapsed_ms = (time.perf_counter() - start) * 1000
                        stats.record(elapsed_ms, response.status_code)

                    except Exception as e:
                        elapsed_ms = (time.perf_counter() - start) * 1000
                        stats.record(elapsed_ms, None, str(e))

        # Start workers
        workers = [asyncio.create_task(worker(i)) for i in range(concurrency)]

        # Run for specified duration
        print(f"Load test running for {duration_seconds} seconds...")
        await asyncio.sleep(duration_seconds)
        stop_event.set()

        # Wait for workers to finish
        await asyncio.gather(*workers, return_exceptions=True)

        # Print results
        print("\n" + "=" * 60)
        print("WRITE LOAD TEST RESULTS")
        print("=" * 60)
        print(stats)
        print(f"\nThroughput: {stats.requests / duration_seconds:.2f} req/sec")

        return stats


async def main() -> None:
    parser = argparse.ArgumentParser(description="Load test for chat archive APIs")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Seed command
    seed_parser = subparsers.add_parser("seed", help="Seed database with test data")
    seed_parser.add_argument(
        "--count", "-n",
        type=int,
        default=10000,
        help="Number of messages to create (default: 10000)",
    )
    seed_parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for inserts (default: 100)",
    )

    # Read load test command
    read_parser = subparsers.add_parser("read", help="Run read API load test")
    read_parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=10,
        help="Number of concurrent workers (default: 10)",
    )
    read_parser.add_argument(
        "--duration", "-d",
        type=int,
        default=60,
        help="Test duration in seconds (default: 60)",
    )

    # Write load test command
    write_parser = subparsers.add_parser("write", help="Run write API load test")
    write_parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=10,
        help="Number of concurrent workers (default: 10)",
    )
    write_parser.add_argument(
        "--duration", "-d",
        type=int,
        default=60,
        help="Test duration in seconds (default: 60)",
    )

    # Full load test command
    full_parser = subparsers.add_parser("full", help="Run full load test (seed + read + write)")
    full_parser.add_argument(
        "--seed-count",
        type=int,
        default=5000,
        help="Number of messages to seed (default: 5000)",
    )
    full_parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=10,
        help="Number of concurrent workers (default: 10)",
    )
    full_parser.add_argument(
        "--duration", "-d",
        type=int,
        default=30,
        help="Test duration in seconds (default: 30)",
    )

    args = parser.parse_args()
    tester = LoadTester(args.base_url)

    if args.command == "seed":
        await tester.seed_database(args.count, args.batch_size)

    elif args.command == "read":
        await tester.run_read_load_test(args.concurrency, args.duration)

    elif args.command == "write":
        await tester.run_write_load_test(args.concurrency, args.duration)

    elif args.command == "full":
        await tester.seed_database(args.seed_count)
        print("\n")
        await tester.run_read_load_test(args.concurrency, args.duration)
        print("\n")
        await tester.run_write_load_test(args.concurrency, args.duration)


if __name__ == "__main__":
    asyncio.run(main())
