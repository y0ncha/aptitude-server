"""Application entrypoint and startup wiring."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging import configure_logging
from app.core.readiness import ReadinessService
from app.core.settings import get_settings, reset_settings_cache
from app.interface.api.health import router as health_router
from app.persistence.db import SQLAlchemyDatabaseReadinessProbe, dispose_engine, init_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize process-wide resources and tear them down on shutdown."""
    reset_settings_cache()
    settings = get_settings()
    configure_logging(settings.log_level)
    init_engine(settings.database_url)
    logger.info("service startup complete")
    try:
        yield
    finally:
        dispose_engine()
        logger.info("service shutdown complete")


def create_app() -> FastAPI:
    """Create and configure a FastAPI application instance."""
    app = FastAPI(title="Aptitude Service", lifespan=lifespan)
    app.state.readiness_service = ReadinessService(
        database_probe=SQLAlchemyDatabaseReadinessProbe(),
    )
    app.include_router(health_router)
    return app


app = create_app()
