# 🐛 ZooBuddy — Отчёт об ошибках

## Баг 1: Кнопки питомца падают при наличии даты рождения (КРИТИЧНЫЙ)

**Симптом:** При нажатии «📊 Статистика», «✏️ Редактировать», «🎯 Вес-цель», «🗑 Удалить» — показывается ошибка.

**Причина:** Функция `format_date()` в `bot/bot/utils/helpers.py:67-71` принимает только объекты `date`, но получает **строки** (`"2020-05-15"`) из JSON API.

```python
# helpers.py — текущий код:
def format_date(d: date | None) -> str:
    if d is None:
        return "—"
    return d.strftime("%d.%m.%Y")  # ← ПАДАЕТ если d — строка
```

Когда у питомца есть `birth_date`, вызов `format_date(pet.get('birth_date'))` получает строку `"2020-05-15"`, и `.strftime()` падает с `AttributeError`. `ErrorGuardMiddleware` перехватывает ошибку и показывает пользователю: «Произошла ошибка. Повторите действие через несколько секунд.»

**Где ломается:** Все 35+ вызовов `format_date()` в `bot/bot/handlers/` при работе с данными из API:
- `pets.py` — профиль, статистика, экспорт
- `reminders.py` — просмотр напоминания
- `food.py` — записи питания
- `medical.py` — медкарта

**Та же проблема** у `format_datetime()` (8 вызовов): `bot/bot/utils/helpers.py:74-78`.

**Исправление:**
```python
def format_date(d: date | str | None) -> str:
    if d is None:
        return "—"
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d)
        except ValueError:
            return d
    return d.strftime("%d.%m.%Y")
```

---

## Баг 2: AI-сервисы всегда «недоступны» — нет API-ключа (ОЖИДАЕМО)

**Симптом:** Все 5 кнопок AI (Фото-анализ, Подбор питания, AI-консультант, Анализы, Голосовые) показывают: «⚠️ AI-функции временно недоступны.»

**Причина:** В `.env` не указаны `OPENAI_API_KEY` или `OPENROUTER_API_KEY`. Эндпоинт `/services/health/ai` возвращает `{"operational": false}`.

Код проверки в `backend/backend/services/provider_health.py:120-121`:
```python
if not _settings.OPENAI_API_KEY and not _settings.OPENROUTER_API_KEY:
    return False
```

**Это не баг кода, а проблема конфигурации.** Нужно добавить API-ключ в `.env`:
```
OPENROUTER_API_KEY=sk-or-...
# или
OPENAI_API_KEY=sk-...
```

---

## Баг 3: Напоминания никогда не отправляются (КРИТИЧНЫЙ)

**Симптом:** Напоминание от февраля до сих пор в статусе «активно», уведомления не приходили.

**Три причины:**

### 3a. Worker не подхватывает новые напоминания
`worker/worker/tasks/reminders.py:83-97` — `load_all_reminders()` вызывается **только один раз при запуске** worker'а. Напоминания, созданные после запуска, **никогда не попадают в планировщик**.

В `worker/worker/main.py:37`:
```python
await load_all_reminders(scheduler)  # Только при старте!
```

Нет механизма (polling, webhook, Redis pub/sub) для обнаружения новых напоминаний.

### 3b. Просроченные одноразовые напоминания зависают навсегда
`worker/worker/tasks/reminders.py:58-61`:
```python
if reminder.repeat == "once":
    if dt <= datetime.now():
        return  # ← Пропускаем, НО is_active не меняем!
```

Просроченные напоминания пропускаются при загрузке, но остаются `is_active=True`. Пользователь видит «АКТИВНО», хотя напоминание никогда не сработает.

### 3c. Несоответствие таймзон
Worker настроен с `timezone=settings.BOT_TIMEZONE` (Europe/Moscow), но `datetime.now()` в контейнере возвращает **UTC**. Это может приводить к тому, что актуальные напоминания ошибочно считаются просроченными (или наоборот).

**Исправление:**
1. Добавить периодическую задачу для подхвата новых напоминаний (каждые 30-60 сек)
2. Деактивировать просроченные одноразовые напоминания
3. Использовать timezone-aware сравнение дат

---

## Баг 4: Бот импортирует backend-код напрямую (АРХИТЕКТУРНЫЙ)

**Симптом:** Нет видимых ошибок сейчас (backend установлен в bot-контейнере), но это нарушает архитектуру.

**Где:** 11 прямых импортов `from backend.backend.services...` в bot-хендлерах:
- `photo.py` — `vision.analyze_pet_photo`, `consult_symptoms`, etc.
- `analysis.py` — `vision.analyze_medical_test`
- `voice.py` — `vision.transcribe_voice`
- `tips.py` — `content.FAQ_TEXT`, `NUTRITION_TEXT`, `TIPS`
- `weight_goal.py` — `norms.weight_progress`
- `emergency.py` — `clinics.search_and_format`, `content.EMERGENCY_*`
- `food.py` — `charts.generate_feeding_chart`, `charts.generate_daily_timeline`
- `compare.py` — `vision.compare_two_foods`
- `pets.py` — `pdf_export.generate_pet_pdf`

**Проблемы:**
- AI-вызовы (`vision.*`) выполняются В КОНТЕЙНЕРЕ БОТА, минуя backend API
- Обход rate-limiting, access control и мониторинга backend'а
- Нарушение изоляции сервисов из `docker-compose.yml`

**Рекомендация:** Все вызовы backend-функций должны идти через `api_client.py` → HTTP API.

---

## Баг 5: Дополнительные мелкие проблемы

### 5a. Возраст в `age_str()` — неправильное склонение
`shared/zoo_shared/db/models.py:60`:
```python
y_word = "год" if years % 10 == 1 and years != 11 else "лет"
```
Для 21, 31, 41... показывается «1 год», но для 111, 211 тоже — хотя должно быть «лет».
Правильно: `and years % 100 != 11`.

### 5b. `format_datetime` тоже падает на строках
`bot/bot/utils/helpers.py:74-78` — аналогичная проблема, что и `format_date`.
Затрагивает: просмотр напоминания, записи питания и воды.
