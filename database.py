"""Инициализация базы данных и управление сессиями."""

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _ensure_schema(conn) -> None:
    """Точечные миграции для существующих инсталляций."""

    def _sync(sync_conn):
        inspector = inspect(sync_conn)
        if "user_settings" not in inspector.get_table_names():
            return

        columns = {col["name"] for col in inspector.get_columns("user_settings")}
        if "plan_tier" not in columns:
            sync_conn.execute(
                text(
                    "ALTER TABLE user_settings "
                    "ADD COLUMN plan_tier VARCHAR(20) NOT NULL DEFAULT 'free'"
                )
            )

        sync_conn.execute(
            text(
                "UPDATE user_settings "
                "SET plan_tier='free' "
                "WHERE plan_tier IS NULL OR TRIM(plan_tier)=''"
            )
        )

    await conn.run_sync(_sync)


async def init_db():
    """Создаёт таблицы и применяет совместимые миграции."""
    from models.models import Base  # noqa: F811

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_schema(conn)


def get_session() -> AsyncSession:
    """Возвращает открытую сессию БД.

    Закрытие сессии должно выполняться вызывающей стороной.
    """
    return async_session()
