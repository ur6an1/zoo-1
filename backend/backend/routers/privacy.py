"""Privacy / 152-ФЗ — удаление данных пользователя по запросу.

Не публикуется на host (backend во внутренней docker-сети); вызывается ботом
после подтверждения пользователем в /delete_me.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.services.account import delete_user_data

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.post("/delete_user/{user_id}")
async def delete_user(user_id: int):
    return {"deleted": await delete_user_data(user_id)}
