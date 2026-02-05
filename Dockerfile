# syntax=docker/dockerfile:1.7

# Build stage - install dependencies
FROM python:3.14-slim AS builder

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

# Set uv environment variables for optimization
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies first (cached layer)
# Copy only dependency files to maximize cache hits
COPY pyproject.toml uv.lock ./

# Install dependencies without the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project --frozen

# Copy application code and metadata needed for build
COPY README.md ./
COPY chat_archive/ chat_archive/

# Install the project (uses cached dependencies)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen


# Runtime stage - minimal image
FROM python:3.14-slim AS runtime

# Labels for container metadata
LABEL org.opencontainers.image.title="Chat Archive Service" \
      org.opencontainers.image.description="API for storing and retrieving chat messages" \
      org.opencontainers.image.version="1.0.0"

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/chat_archive /app/chat_archive
COPY --from=builder --chown=appuser:appgroup /app/pyproject.toml /app/pyproject.toml

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run migrations and start server
CMD ["sh", "-c", "alembic -c chat_archive/infrastructure/migrations/alembic.ini upgrade head && uvicorn chat_archive.main:app --host 0.0.0.0 --port 8000"]
