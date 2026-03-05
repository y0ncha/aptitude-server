"""Integration coverage for Alembic migration lifecycle."""

from __future__ import annotations

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command


@pytest.mark.integration
def test_migrations_upgrade_and_downgrade(require_integration_database: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", require_integration_database)

    command.downgrade(config, "base")
    command.upgrade(config, "head")

    upgraded_engine = create_engine(require_integration_database)
    try:
        inspector = inspect(upgraded_engine)
        assert "audit_events" in inspector.get_table_names()
    finally:
        upgraded_engine.dispose()

    command.downgrade(config, "base")

    downgraded_engine = create_engine(require_integration_database)
    try:
        inspector = inspect(downgraded_engine)
        assert "audit_events" not in inspector.get_table_names()
    finally:
        downgraded_engine.dispose()
