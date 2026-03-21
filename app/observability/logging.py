"""Logging bootstrap helpers."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from logging.config import dictConfig
from typing import TYPE_CHECKING, Any, Literal

from app.observability.context import get_request_context

if TYPE_CHECKING:
    from logging import LogRecord

DEFAULT_LOG_LEVEL = logging.INFO
LogFormat = Literal["auto", "json", "pretty"]
LOG_FORMAT_VALUES: tuple[LogFormat, ...] = ("auto", "json", "pretty")
MANAGED_LOGGER_NAMES: tuple[str, ...] = (
    "app",
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "fastapi",
    "watchfiles",
    "watchfiles.main",
    "sqlalchemy",
    "psycopg",
)


class ObservabilityContextFilter(logging.Filter):
    """Attach request-scoped observability fields to each log record."""

    def filter(self, record: LogRecord) -> bool:
        context = get_request_context()
        record.request_id = context.request_id
        record.http_method = context.http_method
        record.http_route = context.http_route
        record.status_code = context.status_code
        record.duration_ms = context.duration_ms
        if not hasattr(record, "event_type"):
            record.event_type = None
        return True


class JsonLogFormatter(logging.Formatter):
    """Serialize application logs as JSON objects."""

    def format(self, record: LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "http_method": getattr(record, "http_method", None),
            "http_route": getattr(record, "http_route", None),
            "status_code": getattr(record, "status_code", None),
            "duration_ms": getattr(record, "duration_ms", None),
        }
        event_type = getattr(record, "event_type", None)
        if event_type is not None:
            payload["event_type"] = event_type
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class PrettyLogFormatter(logging.Formatter):
    """Render logs in a compact human-readable console format."""

    def format(self, record: LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        base = f"{timestamp} {record.levelname:<5} {record.name} {record.getMessage()}"
        extras = self._extra_fields(record)
        if not extras:
            return base
        return f"{base} | {' '.join(extras)}"

    def _extra_fields(self, record: LogRecord) -> list[str]:
        extras: list[str] = []
        http_method = getattr(record, "http_method", None)
        http_route = getattr(record, "http_route", None)
        status_code = getattr(record, "status_code", None)
        duration_ms = getattr(record, "duration_ms", None)
        request_id = getattr(record, "request_id", None)
        if http_method:
            extras.append(f"method={http_method}")
        if http_route:
            extras.append(f"route={http_route}")
        if status_code is not None:
            extras.append(f"status={status_code}")
        if duration_ms is not None:
            extras.append(f"duration_ms={duration_ms}")
        if request_id:
            extras.append(f"request_id={request_id}")
        event_type = getattr(record, "event_type", None)
        if event_type is not None:
            extras.append(f"event={event_type}")
        if record.exc_info:
            extras.append(f"exception={self.formatException(record.exc_info)}")
        return extras


def _resolve_level(level: str) -> int:
    """Resolve a string level name to a stdlib logging constant."""
    return getattr(logging, level.upper(), DEFAULT_LOG_LEVEL)


def _noisy_library_level(resolved_level: int) -> int:
    """Clamp noisy framework loggers to WARNING unless the app runs in DEBUG."""
    return logging.WARNING if resolved_level > logging.DEBUG else resolved_level


def build_logging_config(
    level: str,
    *,
    log_format: LogFormat = "auto",
    app_env: str = "dev",
    interactive: bool | None = None,
) -> dict[str, Any]:
    """Return logging config with one shared formatter across app and libraries."""
    resolved_level = _resolve_level(level)
    noisy_library_level = _noisy_library_level(resolved_level)
    formatter_name = _formatter_path(
        log_format=log_format,
        app_env=app_env,
        interactive=interactive,
    )
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "observability": {
                "()": "app.observability.logging.ObservabilityContextFilter",
            },
        },
        "formatters": {
            "default": {
                "()": formatter_name,
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "filters": ["observability"],
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "handlers": ["default"],
            "level": resolved_level,
        },
        "loggers": {
            "app": {
                "handlers": ["default"],
                "level": resolved_level,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["default"],
                "level": resolved_level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["default"],
                "level": resolved_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["default"],
                "level": resolved_level,
                "propagate": False,
            },
            "fastapi": {
                "handlers": ["default"],
                "level": resolved_level,
                "propagate": False,
            },
            "watchfiles": {
                "handlers": ["default"],
                "level": noisy_library_level,
                "propagate": False,
            },
            "watchfiles.main": {
                "handlers": ["default"],
                "level": noisy_library_level,
                "propagate": False,
            },
            "sqlalchemy": {
                "handlers": ["default"],
                "level": noisy_library_level,
                "propagate": False,
            },
            "psycopg": {
                "handlers": ["default"],
                "level": noisy_library_level,
                "propagate": False,
            },
        },
    }


def configure_logging(
    level: str,
    *,
    log_format: LogFormat = "auto",
    app_env: str = "dev",
    interactive: bool | None = None,
) -> None:
    """Configure process logging with a deterministic format."""
    _reset_logging_handlers()
    dictConfig(
        build_logging_config(
            level,
            log_format=log_format,
            app_env=app_env,
            interactive=interactive,
        )
    )


def normalize_log_format(value: str | None) -> LogFormat:
    """Return a supported log format value, defaulting invalid input to auto."""
    if value == "auto":
        return "auto"
    if value == "json":
        return "json"
    if value == "pretty":
        return "pretty"
    return "auto"


def _reset_logging_handlers() -> None:
    """Clear existing handlers so repeated reconfiguration rebinds stdout cleanly."""
    logging.getLogger().handlers.clear()
    logger_dict = logging.root.manager.loggerDict
    for logger_name in MANAGED_LOGGER_NAMES:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.disabled = False
    for logger_name, candidate in logger_dict.items():
        if not isinstance(candidate, logging.Logger):
            continue
        if not any(
            logger_name == managed_name or logger_name.startswith(f"{managed_name}.")
            for managed_name in MANAGED_LOGGER_NAMES
        ):
            continue
        logger = candidate
        logger.handlers.clear()
        logger.disabled = False
        if logger_name not in MANAGED_LOGGER_NAMES:
            logger.setLevel(logging.NOTSET)
            logger.propagate = True


def _formatter_path(
    *,
    log_format: LogFormat,
    app_env: str,
    interactive: bool | None,
) -> str:
    resolved_format = _resolve_log_format(
        log_format=log_format,
        app_env=app_env,
        interactive=interactive,
    )
    if resolved_format == "pretty":
        return "app.observability.logging.PrettyLogFormatter"
    return "app.observability.logging.JsonLogFormatter"


def _resolve_log_format(
    *,
    log_format: LogFormat,
    app_env: str,
    interactive: bool | None,
) -> Literal["json", "pretty"]:
    if log_format != "auto":
        return log_format
    if app_env == "container":
        return "json"
    if interactive is None:
        interactive = sys.stdout.isatty()
    return "pretty" if interactive else "json"
