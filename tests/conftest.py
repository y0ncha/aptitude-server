"""Shared pytest fixtures for the service skeleton."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/aptitude"


def _database_is_available(database_url: str) -> bool:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
    finally:
        engine.dispose()


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    """Ensure tests never share cached settings state."""
    from app.core.settings import reset_settings_cache

    reset_settings_cache()
    yield
    reset_settings_cache()


@pytest.fixture(scope="session")
def integration_database_url() -> str:
    """Return a PostgreSQL URL used by integration tests."""
    return os.getenv("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


@pytest.fixture(scope="session")
def require_integration_database(integration_database_url: str) -> str:
    """Skip integration tests when PostgreSQL is not reachable."""
    if not _database_is_available(integration_database_url):
        pytest.skip(
            "PostgreSQL is not reachable for integration tests. "
            "Run `make db-up` and set TEST_DATABASE_URL if needed.",
        )
    return integration_database_url
