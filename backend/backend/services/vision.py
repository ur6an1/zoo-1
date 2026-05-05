"""Сервис AI-анализа через OpenRouter/OpenAI."""

import base64
import logging

import aiohttp
from zoo_shared.config import get_settings

_settings = get_settings()

logger = logging.getLogger(__name__)

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=60)


def has_any_ai() -> bool:
    """Есть ли хотя бы один AI-ключ."""
    return bool(_settings.OPENROUTER_API_KEY or _settings.OPENAI_API_KEY)


def _provider() -> str | None:
    if _settings.OPENROUTER_API_KEY:
        return "openrouter"
    if _settings.OPENAI_API_KEY:
        return "openai"
    return None


def _chat_url() -> str:
    if _provider() == "openrouter":
        return f"{_settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
    return OPENAI_URL


def _chat_model() -> str:
    if _provider() == "openrouter":
        return _settings.OPENROUTER_MODEL
    return _settings.OPENAI_MODEL


def _chat_headers() -> dict[str, str] | None:
    provider = _provider()
    if provider == "openrouter":
        headers = {
            "Authorization": f"Bearer {_settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        if _settings.OPENROUTER_SITE_URL:
            headers["HTTP-Referer"] = _settings.OPENROUTER_SITE_URL
        if _settings.OPENROUTER_APP_NAME:
            headers["X-Title"] = _settings.OPENROUTER_APP_NAME
        return headers
    if provider == "openai":
        return {
            "Authorization": f"Bearer {_settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
    return None


async def _request_chat_completion(messages: list[dict], max_tokens: int) -> str | None:
    headers = _chat_headers()
    if not headers:
        return None

    payload = {
        "model": _chat_model(),
        "max_tokens": max_tokens,
        "messages": messages,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                _chat_url(),
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    logger.error("AI request error %s: %s", resp.status, err[:400])
                    return None
                data = await resp.json()
                choices = data.get("choices", [])
                if not choices:
                    return None
                return choices[0].get("message", {}).get("content", "").strip()
    except Exception as e:
        logger.error("AI request exception: %s", e)
        return None


# ── Промпты ──

PET_ANALYSIS_PROMPT = """Ты — опытный ветеринарный специалист и эксперт по породам животных.
Проанализируй это фото и дай подробный ответ на РУССКОМ языке.

Определи и опиши:
1. 🐾 **Вид животного** (кошка, собака, птица, грызун и т.д.)
2. 🏷 **Предполагаемая порода** (или смесь пород)
3. 📅 **Примерный возраст**
4. ⚖️ **Примерная оценка телосложения** (худое, нормальное, избыточный вес)
5. 🎨 **Окрас и тип шерсти**
6. 👀 **Видимое состояние здоровья** (на основе того, что видно на фото: глаза, шерсть, нос, уши)
7. 💡 **Рекомендации по уходу** (2-3 совета, специфичных для этой породы/вида)

⚕️ В конце обязательно добавь дисклеймер: точную диагностику может провести только ветеринарный врач.

Отвечай дружелюбно, с эмодзи, структурированно."""

FOOD_ANALYSIS_PROMPT = """Ты — эксперт по питанию домашних животных.
Проанализируй фото корма/еды для питомца и ответь на РУССКОМ языке:

1. 🍽 **Что на фото** — определи тип корма или еды
2. ✅ **Подходит ли** — для кошек/собак/других питомцев
3. ⚖️ **Примерная порция** — оценка количества на фото
4. ⚠️ **Предупреждения** — если есть что-то потенциально опасное
5. 💡 **Рекомендации** — советы по кормлению

⚕️ Добавь: для точного подбора рациона обратитесь к ветеринарному диетологу.

Отвечай кратко, дружелюбно, с эмодзи."""


def _make_nutrition_prompt(pet_info: str) -> str:
    return f"""Ты — профессиональный ветеринарный диетолог.

Пользователь отправил фото корма/еды. Вот данные о его питомце:
{pet_info}

Проанализируй фото корма и дай ПОДРОБНЫЙ ответ на РУССКОМ языке:

1. 🍽 **Что на фото** — определи корм, бренд (если видно), класс корма
2. 📋 **Состав** — оцени качество состава, если видна этикетка
3. ✅ **Подходит ли этот корм** — именно для этого питомца (с учётом вида, породы, возраста, веса)
4. ⚖️ **Рекомендуемая порция** — ТОЧНЫЙ расчёт суточной нормы в граммах:
   - Суточная норма (г/день)
   - Разовая порция (если 2 кормления)
   - В мерных стаканах (примерно)
5. 📅 **Режим кормления** — сколько раз в день, в какое время лучше
6. 💧 **Норма воды** — сколько мл воды в день нужно
7. ⚠️ **Предупреждения** — что не так с этим кормом (если есть проблемы)
8. 💡 **Альтернативы** — если корм не идеален, предложи 2-3 лучших варианта

⚕️ Данные рекомендации носят справочный характер. Для индивидуального рациона обратитесь к ветеринарному диетологу.

Отвечай структурированно, с эмодзи, дружелюбно. Будь конкретен в цифрах порций!"""


def _make_symptoms_prompt(pet_info: str) -> str:
    return f"""Ты — опытный ветеринарный врач-консультант.

Вот данные о питомце:
{pet_info}

Пользователь описывает симптомы или ситуацию. Дай ПОДРОБНЫЙ ответ на РУССКОМ языке:

1. 🔍 **Анализ симптомов** — что могут означать описанные симптомы
2. 📋 **Возможные причины** — от частых к редким
3. ⚠️ **Степень срочности**:
   - 🟢 Не срочно — можно наблюдать дома
   - 🟡 Внимание — стоит показать ветеринару в ближайшие дни
   - 🔴 Срочно — нужен ветеринар сегодня/сейчас
4. 🏠 **Что можно сделать дома** — первая помощь
5. ❌ **Чего НЕ делать** — распространённые ошибки
6. 🏥 **Когда точно к ветеринару** — тревожные сигналы
7. 💊 **Что может назначить ветеринар** — обследования/анализы

⚕️ ДИСКЛЕЙМЕР: Эта информация НЕ заменяет очный осмотр! При сомнениях обращайтесь в клинику.

Отвечай развёрнуто, структурированно, с эмодзи."""


# ══════════════════════════════════════════════
#  OPENAI (GPT) API
# ══════════════════════════════════════════════


async def _gpt_photo(image_b64: str, prompt: str) -> str | None:
    """Запрос к vision-модели через активный AI-провайдер."""
    if not has_any_ai():
        return None

    return await _request_chat_completion(
        [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_b64}",
                        "detail": "high",
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }],
        max_tokens=_settings.AI_MAX_TOKENS_VISION,
    )


async def _gpt_text(user_text: str, system_prompt: str) -> str | None:
    """Текстовый запрос через активный AI-провайдер."""
    if not has_any_ai():
        return None

    return await _request_chat_completion(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        max_tokens=_settings.AI_MAX_TOKENS_TEXT,
    )


async def _dual_photo(image_bytes: bytes, prompt: str) -> str | None:
    """Отправляет фото в GPT и возвращает ответ."""
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    return await _gpt_photo(image_b64, prompt)


async def _dual_text(user_text: str, system_prompt: str) -> str | None:
    """Отправляет текст в GPT и возвращает ответ."""
    return await _gpt_text(user_text, system_prompt)


# ══════════════════════════════════════════════
#  ПУБЛИЧНЫЙ API (используется обработчиками)
# ══════════════════════════════════════════════


async def analyze_pet_photo(image_bytes: bytes) -> str | None:
    """Анализ фото питомца."""
    return await _dual_photo(image_bytes, PET_ANALYSIS_PROMPT)


async def analyze_food_photo(image_bytes: bytes) -> str | None:
    """Анализ фото корма/еды."""
    return await _dual_photo(image_bytes, FOOD_ANALYSIS_PROMPT)


async def analyze_food_for_pet(image_bytes: bytes, pet_info: str) -> str | None:
    """Подбор питания."""
    prompt = _make_nutrition_prompt(pet_info)
    return await _dual_photo(image_bytes, prompt)


async def consult_symptoms(symptoms_text: str, pet_info: str) -> str | None:
    """Консультация по симптомам."""
    prompt = _make_symptoms_prompt(pet_info)
    return await _dual_text(symptoms_text, prompt)


# ══════════════════════════════════════════════
#  СРАВНЕНИЕ КОРМОВ
# ══════════════════════════════════════════════

COMPARE_PROMPT = """Ты — эксперт по питанию домашних животных.
Тебе даны фото ДВУХ кормов. Сравни их и дай подробный ответ на РУССКОМ языке:

1. 🍽 **Корм 1** — что это, бренд, класс
2. 🍽 **Корм 2** — что это, бренд, класс
3. ⚖️ **Сравнение** — состав, качество белка, цена/качество
4. 🏆 **Победитель** — какой корм лучше и почему
5. 💡 **Рекомендация** — для каких питомцев подходит каждый

Отвечай структурированно, с эмодзи."""


async def compare_two_foods(image1_bytes: bytes, image2_bytes: bytes) -> str | None:
    """Сравнение двух кормов по фото (отправляем оба в одном запросе)."""
    if not has_any_ai():
        return None

    img1_b64 = base64.b64encode(image1_bytes).decode("utf-8")
    img2_b64 = base64.b64encode(image2_bytes).decode("utf-8")

    return await _request_chat_completion(
        [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Первый корм:"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img1_b64}", "detail": "high"}},
                {"type": "text", "text": "Второй корм:"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img2_b64}", "detail": "high"}},
                {"type": "text", "text": COMPARE_PROMPT},
            ],
        }],
        max_tokens=_settings.AI_MAX_TOKENS_VISION,
    )


# ══════════════════════════════════════════════
#  AI-АНАЛИЗ МЕДИЦИНСКИХ АНАЛИЗОВ
# ══════════════════════════════════════════════

MEDICAL_TEST_PROMPT = """Ты — ветеринарный лаборант-эксперт.
Пользователь отправил фото результатов АНАЛИЗОВ питомца (кровь, моча, биохимия и т.д.).

Данные о питомце:
{pet_info}

Проанализируй фото и дай ПОДРОБНЫЙ ответ на РУССКОМ языке:

1. 📋 **Что на фото** — определи тип анализа
2. 🔬 **Расшифровка** — расшифруй все видимые показатели
3. ✅ **Норма/Отклонения** — какие показатели в норме, какие нет
4. ⚠️ **На что обратить внимание** — самые важные отклонения
5. 🏥 **Рекомендации** — что обсудить с ветеринаром
6. 📊 **Общая оценка** — насколько результаты хорошие

⚕️ ДИСКЛЕЙМЕР: Это предварительная расшифровка. Окончательную интерпретацию даёт только ветеринарный врач!

Отвечай структурированно, с эмодзи."""


async def analyze_medical_test(image_bytes: bytes, pet_info: str) -> str | None:
    """Расшифровка медицинских анализов питомца."""
    prompt = MEDICAL_TEST_PROMPT.format(pet_info=pet_info)
    return await _dual_photo(image_bytes, prompt)


# ══════════════════════════════════════════════
#  ТРАНСКРИПЦИЯ ГОЛОСА (OpenAI Whisper)
# ══════════════════════════════════════════════


async def transcribe_voice(voice_bytes: bytes) -> str | None:
    """Транскрибирует голосовое сообщение через OpenAI Whisper API."""
    from services.voice import transcribe_voice as _transcribe_voice

    return await _transcribe_voice(voice_bytes)
