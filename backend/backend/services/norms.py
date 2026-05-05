"""Расчёт суточных норм еды и воды для питомцев."""


def calc_food_norm(species: str, weight_kg: float | None, age_months: int | None) -> dict:
    """Рассчитывает суточную норму еды (г) и воды (мл).

    Returns:
        {"food_g": int, "water_ml": int, "meals_per_day": int, "description": str}
    """
    if not weight_kg or weight_kg <= 0:
        return {"food_g": 0, "water_ml": 0, "meals_per_day": 2, "description": "Укажите вес питомца для расчёта"}

    w = weight_kg
    is_puppy = age_months is not None and age_months < 12
    is_kitten = age_months is not None and age_months < 12

    if species == "собака":
        if is_puppy:
            food_g = int(w * 40)  # ~4% от веса тела для щенков
            meals = 3 if age_months and age_months < 6 else 2
        elif w < 10:
            food_g = int(w * 30)
            meals = 2
        elif w < 25:
            food_g = int(w * 25)
            meals = 2
        else:
            food_g = int(w * 20)
            meals = 2
        water_ml = int(w * 50)  # 50 мл на кг

    elif species == "кошка":
        if is_kitten:
            food_g = int(w * 50)
            meals = 3 if age_months and age_months < 6 else 2
        else:
            food_g = max(int(w * 30), 40)
            meals = 2
        water_ml = int(w * 40)  # 40 мл на кг

    elif species == "птица":
        food_g = max(int(w * 100), 10)  # ~10% от веса
        water_ml = max(int(w * 50), 10)
        meals = 2

    elif species == "грызун":
        food_g = max(int(w * 50), 5)
        water_ml = max(int(w * 100), 10)
        meals = 2

    else:
        food_g = int(w * 25)
        water_ml = int(w * 50)
        meals = 2

    desc = f"~{food_g} г корма/день, {water_ml} мл воды/день, {meals}x кормление"
    return {"food_g": food_g, "water_ml": water_ml, "meals_per_day": meals, "description": desc}


def calc_progress_bar(current: float, target: float, length: int = 10) -> str:
    """Генерирует текстовый прогресс-бар."""
    if target <= 0:
        return "▱" * length
    pct = min(current / target, 1.0)
    filled = int(pct * length)
    return "▰" * filled + "▱" * (length - filled) + f" {pct:.0%}"


def weight_progress(current: float | None, target: float | None) -> str | None:
    """Прогресс к целевому весу."""
    if not current or not target:
        return None
    diff = abs(current - target)
    if diff < 0.1:
        return "✅ Целевой вес достигнут!"
    if current > target:
        return f"⬇️ Нужно сбросить {diff:.1f} кг (сейчас {current} → цель {target})"
    else:
        return f"⬆️ Нужно набрать {diff:.1f} кг (сейчас {current} → цель {target})"
