"""ZooBuddy Backend — FastAPI REST API."""

import logging
import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.routers import health

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Running Alembic migrations...")
    result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Alembic migration failed: %s", result.stderr)
        raise RuntimeError(f"Alembic migration failed: {result.stderr}")
    logger.info("Alembic migrations applied successfully")
    yield


app = FastAPI(title="ZooBuddy API", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
