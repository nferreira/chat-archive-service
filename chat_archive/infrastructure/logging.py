from __future__ import annotations

import logging
import os
import sys

import structlog


def setup_logging(
    log_level: str | None = None,
    log_format: str | None = None,
) -> None:
    level = (log_level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    # Default to console for local dev (TTY), JSON for production (non-TTY/containers)
    default_fmt = "console" if sys.stderr.isatty() else "console"
    fmt = (log_format or os.environ.get("LOG_FORMAT", default_fmt)).lower()

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if fmt == "console":
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet down noisy loggers (unless in DEBUG mode)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # SQLAlchemy engine logs SQL queries at INFO level when echo=True
    # Keep them visible in DEBUG mode, suppress in other modes
    if level != "DEBUG":
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
