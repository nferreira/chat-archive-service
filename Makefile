.DEFAULT_GOAL := help
SHELL := /bin/bash

APP          := chat_archive.main:app
COMPOSE      := docker compose
ALEMBIC_CFG  := chat_archive/infrastructure/migrations/alembic.ini

# Load .env so Make variables (APP_DB_USER, etc.) are available for targets
# like shell-postgres.  We do NOT export them — DATABASE_URL must come from
# the caller's environment or from engine.py's default, not from .env (which
# has no DATABASE_URL and whose values are meant for Docker Compose).
-include .env

# ──────────────────────────────────────────────
# Help
# ──────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		sed 's/^[^:]*://' | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@printf "\n\033[33mAPI Usage:\033[0m Pass variables using var=value syntax (not --var value)\n"
	@echo "  Examples:"
	@echo "    make store-message user_id=jdoe name='John Doe' question='Hello?' answer='Hi!'"
	@echo "    make get-messages-by-user user_id=jdoe start=2026-01-01 end=2026-02-01 page_size=10"
	@echo "    make get-messages-by-day day=2026-02-04 page_size=20 page=0"
	@echo "    make get-messages-by-period start=2026-01-01 end=2026-02-01 page_size=50 page=2"
	@echo "    make delete-user user_id=jdoe"
	@echo "    make load-seed count=10000"
	@echo "    make load-read concurrency=20 duration=60  # Read test: 20 workers for 60s"
	@echo "    make load-write concurrency=10 duration=30 # Write test: 10 workers for 30s"
	@echo "    make load-full seed_count=5000 concurrency=10 duration=30  # Full test"
	@printf "\n  \033[90mPagination: All get-* targets support page_size= (1-200) and page= (default 0)\033[0m\n"

# ──────────────────────────────────────────────
# Build
# ──────────────────────────────────────────────

.PHONY: install sync lock build clean

install: ## Install all dependencies (incl. dev)
	uv sync

sync: install ## Alias for install

lock: ## Regenerate uv.lock
	uv lock

build: ## Build the Python wheel
	uv build

clean: ## Remove build artefacts, caches, .pyc files
	rm -rf dist/ build/ .eggs/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov

# ──────────────────────────────────────────────
# App
# ──────────────────────────────────────────────

.PHONY: run dev migrate migrate-down revision

run: ## Start the app (production-like)
	uv run uvicorn $(APP) --host 0.0.0.0 --port 8000

dev: ## Start the app with auto-reload
	uv run uvicorn $(APP) --host 0.0.0.0 --port 8000 --reload

migrate: ## Run alembic migrations (upgrade head)
	uv run alembic -c $(ALEMBIC_CFG) upgrade head

migrate-down: ## Rollback one alembic migration
	uv run alembic -c $(ALEMBIC_CFG) downgrade -1

revision: ## Create a new alembic migration (usage: make revision msg="add foo")
	uv run alembic -c $(ALEMBIC_CFG) revision --autogenerate -m "$(msg)"

# ──────────────────────────────────────────────
# Test
# ──────────────────────────────────────────────

.PHONY: test test-v test-cov test-cov-html

test: ## Run all tests
	uv run pytest

test-v: ## Run tests with verbose output
	uv run pytest -v

test-cov: ## Run tests with coverage report
	uv run pytest --cov=chat_archive --cov-report=term-missing

test-cov-html: ## Run tests with HTML coverage report
	uv run pytest --cov=chat_archive --cov-report=html
	@echo "Open htmlcov/index.html in your browser"

# ──────────────────────────────────────────────
# Lint / Format
# ──────────────────────────────────────────────

.PHONY: lint format check

lint: ## Run ruff linter
	uv run ruff check .

format: ## Run ruff formatter
	uv run ruff format .

check: lint ## Run all static checks
	uv run ruff format --check .

# ──────────────────────────────────────────────
# Docker
# ──────────────────────────────────────────────

.PHONY: docker-build docker-run docker-stop docker-clean

docker-build: ## Build the app Docker image
	docker build -t chat-archive .

docker-run: ## Build and run app + db with Docker Compose (foreground)
	$(COMPOSE) up --build

docker-stop: ## Stop all containers started with docker run
	docker ps -q --filter ancestor=chat-archive | xargs -r docker stop

docker-clean: ## Remove the app Docker image
	docker rmi -f chat-archive 2>/dev/null || true

# ──────────────────────────────────────────────
# Docker Compose
# ──────────────────────────────────────────────

.PHONY: up down restart logs ps build-up

up: ## Start all services (db + app) in the background
	$(COMPOSE) up -d

build-up: ## Rebuild and start all services
	$(COMPOSE) up -d --build

down: ## Stop and remove all services
	$(COMPOSE) down

restart: ## Restart all services
	$(COMPOSE) restart

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

ps: ## Show running containers
	$(COMPOSE) ps

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────

.PHONY: db-up db-down db-reset db-logs shell-postgres

db-up: ## Start only the PostgreSQL container
	$(COMPOSE) up -d db

db-down: ## Stop the PostgreSQL container
	$(COMPOSE) stop db

db-reset: ## Destroy DB volume and recreate from scratch
	$(COMPOSE) down -v
	$(COMPOSE) up -d db

db-logs: ## Tail PostgreSQL logs
	$(COMPOSE) logs -f db

shell-postgres: ## Open a psql shell inside the running PostgreSQL container
	$(COMPOSE) exec db psql -U $(APP_DB_USER) -d $(APP_DB_NAME)

# ──────────────────────────────────────────────
# API
# ──────────────────────────────────────────────
# Usage: Pass variables using var=value syntax (not --var value)
#
# Examples:
#   make store-message user_id=jdoe name='John Doe' question='Hello?' answer='Hi!'
#   make get-messages-by-user user_id=jdoe start=2026-01-01 end=2026-02-01 page_size=10
#   make get-messages-by-day day=2026-02-04 page_size=20 page=0
#   make get-messages-by-period start=2026-01-01 end=2026-02-01 page_size=50 page=2
#   make delete-user user_id=jdoe
#
# Pagination: All get-* targets support page_size= (1-200) and page= (default 0)
# ──────────────────────────────────────────────

.PHONY: store-message get-messages-by-user get-messages-by-day get-messages-by-period delete-user

store-message: ## Store a message (user_id= name= question= answer=)
	@./scripts/store-message.sh --user-id "$(user_id)" --name "$(name)" --question "$(question)" --answer "$(answer)"

get-messages-by-user: ## Get user messages (user_id= start= end= [page_size=] [page=])
	@./scripts/get-messages-by-user.sh --user-id "$(user_id)" --start "$(start)" --end "$(end)" $(if $(page_size),--page-size $(page_size)) $(if $(page),--page $(page))

get-messages-by-day: ## Get messages by day (day= [page_size=] [page=])
	@./scripts/get-messages-by-day.sh --day "$(day)" $(if $(page_size),--page-size $(page_size)) $(if $(page),--page $(page))

get-messages-by-period: ## Get messages by period (start= end= [page_size=] [page=])
	@./scripts/get-messages-by-period.sh --start "$(start)" --end "$(end)" $(if $(page_size),--page-size $(page_size)) $(if $(page),--page $(page))

delete-user: ## Delete a user (user_id=)
	@./scripts/delete-user.sh --user-id "$(user_id)"

# ──────────────────────────────────────────────
# Load Test
# ──────────────────────────────────────────────
# Usage: Seed database and stress test APIs
#
# Examples:
#   make load-seed count=10000           # Seed with 10k messages
#   make load-read concurrency=20 duration=60  # Read test: 20 workers for 60s
#   make load-write concurrency=10 duration=30 # Write test: 10 workers for 30s
#   make load-full seed_count=5000 concurrency=10 duration=30  # Full test
# ──────────────────────────────────────────────

.PHONY: load-seed load-read load-write load-full

load-seed: ## Seed database with test data (count=10000)
	uv run python scripts/load_test.py seed --count $(or $(count),10000)

load-read: ## Run read API load test (concurrency=10 duration=60)
	uv run python scripts/load_test.py read --concurrency $(or $(concurrency),10) --duration $(or $(duration),60)

load-write: ## Run write API load test (concurrency=10 duration=60)
	uv run python scripts/load_test.py write --concurrency $(or $(concurrency),10) --duration $(or $(duration),60)

load-full: ## Run full load test (seed_count=5000 concurrency=10 duration=30)
	uv run python scripts/load_test.py full --seed-count $(or $(seed_count),5000) --concurrency $(or $(concurrency),10) --duration $(or $(duration),30)
