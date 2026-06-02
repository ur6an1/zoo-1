"""Internal API key protection for backend routes."""

from __future__ import annotations

import secrets
from collections.abc import Callable

from fastapi import Request
from starlette.responses import JSONResponse, Response
from zoo_shared.config import get_settings

PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


def is_public_path(path: str) -> bool:
    """Paths that must stay available without internal auth."""
    return path in PUBLIC_PATHS


def is_internal_api_authorized(path: str, provided_key: str, expected_key: str) -> bool:
    """Validate internal API access. Empty expected key means auth is disabled."""
    expected = expected_key.strip()
    if not expected or is_public_path(path):
        return True
    return secrets.compare_digest(provided_key, expected)


async def require_internal_api_key(
    request: Request,
    call_next: Callable[[Request], Response],
) -> Response:
    """FastAPI middleware: protect every non-public backend route with a shared key."""
    settings = get_settings()
    provided_key = request.headers.get("X-Internal-API-Key", "")
    if not is_internal_api_authorized(request.url.path, provided_key, settings.INTERNAL_API_KEY):
        return JSONResponse(
            status_code=401,
            content={"detail": "internal api key required"},
        )
    return await call_next(request)
