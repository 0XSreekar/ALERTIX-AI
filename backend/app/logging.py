import logging
import sys
from typing import Any, cast

import structlog
from pythonjsonlogger import jsonlogger

from app.config import get_settings


class _JsonFormatter(jsonlogger.JsonFormatter):
    """JSON log formatter with consistent field names."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("timestamp", self.formatTime(record, self.datefmt))
        log_record["level"] = record.levelname
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno
        # Remove duplicated fields added by the base class
        log_record.pop("levelname", None)
        log_record.pop("name", None)


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    if settings.is_production:
        # JSON output for all stdlib / uvicorn loggers in production
        json_formatter = _JsonFormatter(
            fmt="%(timestamp)s %(level)s %(message)s %(module)s %(function)s %(line)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(json_formatter)

        root_logger = logging.getLogger()
        root_logger.handlers = [handler]
        root_logger.setLevel(level)

        for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
            uvicorn_logger = logging.getLogger(logger_name)
            uvicorn_logger.handlers = [handler]
            uvicorn_logger.setLevel(level)
            uvicorn_logger.propagate = False
    else:
        logging.basicConfig(level=level, format="%(message)s")

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if settings.is_production:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=cast(Any, processors),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
