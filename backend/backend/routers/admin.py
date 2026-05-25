"""Admin REST API — агрегации для админ-панели бота.

Эндпоинты не публикуются на host (backend слушает только во внутренней
docker-сети), а доступ к админке гейтится в боте по ADMIN_IDS — как и
существующий /subscriptions/grant. Дополнительной авторизации здесь нет.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.services.admin_stats import (
    get_broadcast_targets,
    get_finance,
    get_overview,
    get_user_detail,
    list_users,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview")
async def overview():
    return await get_overview()


@router.get("/finance")
async def finance():
    return await get_finance()


@router.get("/users")
async def users(limit: int = 8, offset: int = 0, query: str | None = None):
    return await list_users(limit=limit, offset=offset, query=query)


@router.get("/users/{user_id}")
async def user_detail(user_id: int):
    detail = await get_user_detail(user_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="user not found")
    return detail


@router.get("/broadcast/targets")
async def broadcast_targets():
    return {"user_ids": await get_broadcast_targets()}
