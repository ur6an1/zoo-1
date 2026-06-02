"""Клавиатуры бота: inline и reply."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ──────────────────── ГЛАВНОЕ МЕНЮ (Reply) ────────────────────

main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🐾 Питомцы"), KeyboardButton(text="🩺 Здоровье")],
        [KeyboardButton(text="🤖 AI-сервисы"), KeyboardButton(text="⚙️ Настройки")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите раздел 👇",
)

quick_start_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить питомца", callback_data="pet:add")],
        [InlineKeyboardButton(text="⭐️ Посмотреть подписку", callback_data="settings:subscription")],
        [InlineKeyboardButton(text="🏠 Открыть меню", callback_data="menu:main")],
    ]
)

add_pet_cta_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить питомца", callback_data="pet:add")],
        [InlineKeyboardButton(text="◀️ В меню", callback_data="menu:main")],
    ]
)

pets_hub_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🐾 Мои питомцы", callback_data="pet:list")],
        [InlineKeyboardButton(text="⏰ Напоминания", callback_data="reminder:menu")],
        [InlineKeyboardButton(text="📅 Календарь", callback_data="calendar:view")],
        [InlineKeyboardButton(text="◀️ В меню", callback_data="menu:main")],
    ]
)

health_hub_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🏥 Медкарта", callback_data="med:menu")],
        [InlineKeyboardButton(text="🍽 Дневник питания", callback_data="food:menu")],
        [InlineKeyboardButton(text="🌤 Погода", callback_data="weather:show")],
        [InlineKeyboardButton(text="💡 Советы", callback_data="tips:menu")],
        [InlineKeyboardButton(text="🆘 Экстренная помощь", callback_data="sos:menu")],
        [InlineKeyboardButton(text="◀️ В меню", callback_data="menu:main")],
    ]
)

ai_hub_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📷 Фото-анализ", callback_data="photo:menu")],
        [InlineKeyboardButton(text="🥗 Подбор питания", callback_data="ai:nutrition")],
        [InlineKeyboardButton(text="🩺 AI-консультант", callback_data="ai:symptoms")],
        [InlineKeyboardButton(text="🔬 Анализы", callback_data="analysis:start")],
        [InlineKeyboardButton(text="🎙 Голосовые", callback_data="voice:menu")],
        [InlineKeyboardButton(text="◀️ В меню", callback_data="menu:main")],
    ]
)

settings_hub_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings:menu")],
        [InlineKeyboardButton(text="⭐️ Подписка", callback_data="settings:subscription")],
        [InlineKeyboardButton(text="❌ Отменить подписку", callback_data="settings:sub_cancel")],
        [InlineKeyboardButton(text="◀️ В меню", callback_data="menu:main")],
    ]
)

# ──────────────────── ПИТОМЦЫ ────────────────────


def _get(obj, key, default=""):
    """Access attribute or dict key transparently."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def pets_list_kb(pets: list, action: str = "view") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for pet in pets:
        emoji = _get(pet, "species_emoji", "🐾")
        builder.button(text=f"{emoji} {_get(pet, 'name')}", callback_data=f"pet:{action}:{_get(pet, 'id')}")
    builder.adjust(1)
    if action == "view":
        builder.row(InlineKeyboardButton(text="➕ Добавить питомца", callback_data="pet:add"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main"))
    return builder.as_markup()


def pet_profile_kb(pet_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data=f"pet:stats:{pet_id}")
    builder.button(text="✏️ Редактировать", callback_data=f"pet:edit:{pet_id}")
    builder.button(text="🎯 Вес-цель", callback_data=f"pet:weight_goal:{pet_id}")
    builder.button(text="📤 Экспорт PDF", callback_data=f"pet:export_pdf:{pet_id}")
    builder.button(text="📤 Экспорт TXT", callback_data=f"pet:export:{pet_id}")
    builder.button(text="🗑 Удалить", callback_data=f"pet:confirm_delete:{pet_id}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="◀️ К списку", callback_data="pet:list"))
    return builder.as_markup()


def post_pet_created_kb(pet_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏰ Создать напоминание", callback_data="reminder:add")],
            [InlineKeyboardButton(text="🎯 Поставить цель по весу", callback_data=f"pet:weight_goal:{pet_id}")],
            [InlineKeyboardButton(text="⭐️ Что даёт подписка", callback_data="settings:subscription")],
        ]
    )


def pet_edit_kb(pet_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Имя", callback_data=f"pet:edit_field:name:{pet_id}")
    builder.button(text="🐾 Порода", callback_data=f"pet:edit_field:breed:{pet_id}")
    builder.button(text="📅 Дата рождения", callback_data=f"pet:edit_field:birth:{pet_id}")
    builder.button(text="⚖️ Вес", callback_data=f"pet:edit_field:weight:{pet_id}")
    builder.button(text="📷 Фото", callback_data=f"pet:edit_field:photo:{pet_id}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=f"pet:view:{pet_id}"))
    return builder.as_markup()


def confirm_delete_kb(pet_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"pet:delete:{pet_id}")
    builder.button(text="❌ Отмена", callback_data=f"pet:view:{pet_id}")
    return builder.as_markup()


species_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🐱 Кошка", callback_data="species:кошка"),
            InlineKeyboardButton(text="🐶 Собака", callback_data="species:собака"),
        ],
        [
            InlineKeyboardButton(text="🐦 Птица", callback_data="species:птица"),
            InlineKeyboardButton(text="🐹 Грызун", callback_data="species:грызун"),
        ],
        [InlineKeyboardButton(text="🐾 Другое", callback_data="species:другое")],
    ]
)

# ──────────────────── НАПОМИНАНИЯ ────────────────────

reminders_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="➕ Новое напоминание", callback_data="reminder:add")],
        [InlineKeyboardButton(text="📋 Мои напоминания", callback_data="reminder:list")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
    ]
)

reminder_category_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🍽 Кормление", callback_data="rem_cat:feeding"),
            InlineKeyboardButton(text="💉 Прививка", callback_data="rem_cat:vaccine"),
        ],
        [
            InlineKeyboardButton(text="🏥 Ветеринар", callback_data="rem_cat:vet"),
            InlineKeyboardButton(text="✂️ Груминг", callback_data="rem_cat:grooming"),
        ],
        [InlineKeyboardButton(text="📌 Своё", callback_data="rem_cat:custom")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="reminder:cancel")],
    ]
)

reminder_repeat_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Разово", callback_data="repeat:once"),
            InlineKeyboardButton(text="Ежедневно", callback_data="repeat:daily"),
        ],
        [
            InlineKeyboardButton(text="Еженедельно", callback_data="repeat:weekly"),
            InlineKeyboardButton(text="Ежемесячно", callback_data="repeat:monthly"),
        ],
        [InlineKeyboardButton(text="Ежегодно", callback_data="repeat:yearly")],
    ]
)


def reminders_list_kb(reminders: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for rem in reminders:
        emoji = _get(rem, "category_emoji", "⏰")
        status = "" if _get(rem, "is_active", True) else " ⏸"
        builder.button(text=f"{emoji} {_get(rem, 'title')}{status}", callback_data=f"reminder:view:{_get(rem, 'id')}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="reminder:menu"))
    return builder.as_markup()


def reminder_detail_kb(rem_id: int, is_active: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_active:
        builder.button(text="⏸ Приостановить", callback_data=f"reminder:pause:{rem_id}")
    else:
        builder.button(text="▶️ Возобновить", callback_data=f"reminder:resume:{rem_id}")
    builder.button(text="🗑 Удалить", callback_data=f"reminder:delete:{rem_id}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="reminder:list"))
    return builder.as_markup()


# ──────────────────── МЕДКАРТА ────────────────────

medical_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="💉 Прививки", callback_data="med:vaccines")],
        [InlineKeyboardButton(text="🏥 Визиты к ветеринару", callback_data="med:vetvisits")],
        [InlineKeyboardButton(text="⚖️ Учёт веса", callback_data="med:weight")],
        [InlineKeyboardButton(text="📄 Документы", callback_data="med:documents")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
    ]
)


def med_section_kb(section: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить", callback_data=f"med:{section}:add")
    builder.button(text="📋 История", callback_data=f"med:{section}:list")
    if section == "weight":
        builder.button(text="📊 График", callback_data="med:weight:chart")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="med:menu"))
    return builder.as_markup()


# ──────────────────── ДНЕВНИК ПИТАНИЯ ────────────────────

food_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🍽 Приём пищи", callback_data="food:meal")],
        [InlineKeyboardButton(text="💧 Вода", callback_data="food:water")],
        [InlineKeyboardButton(text="⚠️ Аллергии", callback_data="food:allergies")],
        [InlineKeyboardButton(text="📋 История за сегодня", callback_data="food:today")],
        [InlineKeyboardButton(text="📊 Аналитика", callback_data="food:analytics")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
    ]
)

food_analytics_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📊 Нормы еды/воды", callback_data="food:norms")],
        [InlineKeyboardButton(text="📊 График за неделю", callback_data="food:chart:week")],
        [InlineKeyboardButton(text="📈 Расписание дня", callback_data="food:chart:day")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="food:menu")],
    ]
)

# ──────────────────── AI ФОТО-МЕНЮ ────────────────────

photo_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🐾 Распознать питомца", callback_data="photo:pet")],
        [InlineKeyboardButton(text="🍽 Распознать корм/еду", callback_data="photo:food")],
        [InlineKeyboardButton(text="⚖️ Сравнить 2 корма", callback_data="photo:compare")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
    ]
)

food_action_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить", callback_data="food:meal:add")],
        [InlineKeyboardButton(text="📋 История", callback_data="food:meal:list")],
        [InlineKeyboardButton(text="🗑 Очистить историю", callback_data="food:meal:clear_confirm")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="food:menu")],
    ]
)

water_action_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить", callback_data="food:water:add")],
        [InlineKeyboardButton(text="📋 История", callback_data="food:water:list")],
        [InlineKeyboardButton(text="🗑 Очистить историю", callback_data="food:water:clear_confirm")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="food:menu")],
    ]
)

allergy_action_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить", callback_data="food:allergy:add")],
        [InlineKeyboardButton(text="📋 Список", callback_data="food:allergy:list")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="food:menu")],
    ]
)


def allergy_list_kb(allergies: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for a in allergies:
        builder.button(text=f"🗑 {a.allergen}", callback_data=f"food:allergy:del:{a.id}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="food:allergies"))
    return builder.as_markup()


def food_clear_confirm_kb(section: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, очистить", callback_data=f"food:{section}:clear")
    builder.button(text="❌ Отмена", callback_data=f"food:{section}")
    return builder.as_markup()


# ──────────────────── НАСТРОЙКИ ────────────────────

settings_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⭐️ Подписка", callback_data="settings:subscription")],
        [InlineKeyboardButton(text="❌ Отменить подписку", callback_data="settings:sub_cancel")],
        [InlineKeyboardButton(text="🌤 Погода (город)", callback_data="settings:weather_city")],
        [InlineKeyboardButton(text="🔔 Погодные уведомления", callback_data="settings:weather_toggle")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
    ]
)

# ──────────────────── ЭКСТРЕННАЯ ПОМОЩЬ ────────────────────

emergency_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🏥 Найти ветклинику (рядом)", callback_data="sos:clinic")],
        [InlineKeyboardButton(text="🏥 Клиники с рейтингом", callback_data="sos:clinic_rated")],
        [InlineKeyboardButton(text="💊 Отравление", callback_data="sos:poisoning")],
        [InlineKeyboardButton(text="🩹 Травма", callback_data="sos:injury")],
        [InlineKeyboardButton(text="🌡 Перегрев", callback_data="sos:overheat")],
        [InlineKeyboardButton(text="📋 Общая памятка", callback_data="sos:general")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
    ]
)

location_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📍 Отправить местоположение", request_location=True)],
        [KeyboardButton(text="◀️ Назад в меню")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

# ──────────────────── СОВЕТЫ ────────────────────

tips_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🐱 Кошки", callback_data="tips:кошка")],
        [InlineKeyboardButton(text="🐶 Собаки", callback_data="tips:собака")],
        [InlineKeyboardButton(text="🐦 Птицы", callback_data="tips:птица")],
        [InlineKeyboardButton(text="🐹 Грызуны", callback_data="tips:грызун")],
        [InlineKeyboardButton(text="❓ FAQ", callback_data="tips:faq")],
        [InlineKeyboardButton(text="🍽 Питание по возрасту", callback_data="tips:nutrition")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
    ]
)

# ──────────────────── ОБЩИЕ ────────────────────

skip_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip")]])

cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]])

back_to_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="◀️ В главное меню", callback_data="menu:main")]]
)

doc_type_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🪪 Ветпаспорт", callback_data="doc_type:passport")],
        [InlineKeyboardButton(text="📋 Справка", callback_data="doc_type:certificate")],
        [InlineKeyboardButton(text="📄 Другое", callback_data="doc_type:other")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ]
)

# ──────────────────── КЛИНИКИ (фильтры) ────────────────────

clinic_radius_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="1 км", callback_data="clinic:r:1000"),
            InlineKeyboardButton(text="3 км", callback_data="clinic:r:3000"),
            InlineKeyboardButton(text="5 км", callback_data="clinic:r:5000"),
        ],
        [
            InlineKeyboardButton(text="10 км", callback_data="clinic:r:10000"),
            InlineKeyboardButton(text="20 км", callback_data="clinic:r:20000"),
        ],
    ]
)
