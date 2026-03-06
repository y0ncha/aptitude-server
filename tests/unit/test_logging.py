"""Unit tests for centralized logging configuration."""

from __future__ import annotations

import logging
import sys

import pytest

from app.core.logging import LOG_FORMAT, build_logging_config, configure_logging


@pytest.mark.unit
def test_build_logging_config_sets_shared_uvicorn_handlers() -> None:
    config = build_logging_config("INFO")

    assert config["formatters"]["default"]["format"] == LOG_FORMAT
    assert config["handlers"]["default"]["stream"] == "ext://sys.stdout"
    assert config["loggers"]["uvicorn.error"]["handlers"] == ["default"]
    assert config["loggers"]["uvicorn.access"]["handlers"] == ["default"]
    assert config["loggers"]["uvicorn.error"]["propagate"] is False
    assert config["loggers"]["uvicorn.access"]["propagate"] is False


@pytest.mark.unit
def test_configure_logging_wires_root_and_uvicorn_to_stdout() -> None:
    configure_logging("invalid-level")

    root_logger = logging.getLogger()
    uvicorn_error_logger = logging.getLogger("uvicorn.error")

    assert root_logger.level == logging.INFO
    assert uvicorn_error_logger.level == logging.INFO
    assert uvicorn_error_logger.propagate is False
    assert root_logger.handlers[0].stream is sys.stdout
    assert root_logger.handlers[0].formatter is not None
    assert root_logger.handlers[0].formatter._fmt == LOG_FORMAT  # noqa: SLF001
