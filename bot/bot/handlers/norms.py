"""Обработчики: отображение суточных норм еды и воды."""

import logging
from datetime import date, datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import and_, select
from zoo_shared.db import async_session
from zoo_shared.db.models import FoodEntry, Pet, WaterEntry

from backend.backend.services.norms import calc_food_norm, calc_progress_bar
from bot.keyboards.keyboards import back_to_menu_kb

logger = logging.getLogger(__name__)
router = Router(name="norms")


@router.callback_query(F.data == "food:norms")
async def cb_food_norms(callback: CallbackQuery):
    """Показывает суточные нормы еды/воды и прогресс за сегодня."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Pet).where(Pet.user_id == callback.from_user.id)
            )
            pets = result.scalars().all()

            if not pets:
                await callback.message.edit_text(
                    "😕 У вас нет питомцев.\n"
                    "Сначала добавьте питомца в разделе 🐾 Мои питомцы.",
                    reply_markup=back_to_menu_kb,
                )
                await callback.answer()
                return

            today = date.today()
            today_start = datetime(today.year, today.month, today.day)
            today_end = datetime(today.year, today.month, today.day, 23, 59, 59)

            lines = [f"📊 <b>Нормы еды и воды — {today.strftime('%d.%m.%Y')}</b>\n"]

            for pet in pets:
                norm = calc_food_norm(pet.species, pet.weight, pet.age_months())

                # Еда за сегодня
                food_result = await session.execute(
                    select(FoodEntry).where(
                        and_(
                            FoodEntry.pet_id == pet.id,
                            FoodEntry.meal_time >= today_start,
                            FoodEntry.meal_time <= today_end,
                        )
                    )
                )
                food_entries = food_result.scalars().all()
                food_today_g = sum(
                    e.portion_grams for e in food_entries if e.portion_grams
                )

                # Вода за сегодня
                water_result = await session.execute(
                    select(WaterEntry).where(
                        and_(
                            WaterEntry.pet_id == pet.id,
                            WaterEntry.recorded_at >= today_start,
                            WaterEntry.recorded_at <= today_end,
                        )
                    )
                )
                water_entries = water_result.scalars().all()
                water_today_ml = sum(e.amount_ml for e in water_entries)

                meals_today = len(food_entries)

                lines.append(f"{pet.species_emoji} <b>{pet.name}</b>")

                if norm["food_g"] == 0:
                    lines.append(f"  ⚠️ {norm['description']}")
                else:
                    lines.append(
                        f"  🍽 Норма еды: <b>{norm['food_g']} г/день</b>"
                    )
                    lines.append(
                        f"  💧 Норма воды: <b>{norm['water_ml']} мл/день</b>"
                    )
                    lines.append(
                        f"  🕐 Кормлений в день: <b>{norm['meals_per_day']}</b>"
                    )

                    lines.append("")
                    lines.append("  <b>Прогресс за сегодня:</b>")

                    food_bar = calc_progress_bar(food_today_g, norm["food_g"])
                    lines.append(
                        f"  🍽 Еда: {food_today_g:.0f}/{norm['food_g']} г"
                    )
                    lines.append(f"  {food_bar}")

                    water_bar = calc_progress_bar(water_today_ml, norm["water_ml"])
                    lines.append(
                        f"  💧 Вода: {water_today_ml}/{norm['water_ml']} мл"
                    )
                    lines.append(f"  {water_bar}")

                    lines.append(
                        f"  🍽 Кормлений сегодня: {meals_today}/{norm['meals_per_day']}"
                    )

                lines.append("")

        await callback.message.edit_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=back_to_menu_kb,
        )

    except Exception as e:
        logger.error(f"Ошибка отображения норм: {e}")
        await callback.message.edit_text(
            "😕 Произошла ошибка при расчёте норм. Попробуйте позже.",
            reply_markup=back_to_menu_kb,
        )

    await callback.answer()
