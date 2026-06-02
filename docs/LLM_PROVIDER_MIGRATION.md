# ТЗ: миграция LLM-провайдера на OpenRouter

## 1. Краткое резюме

В проекте LLM-вызовы сосредоточены в **одном пакете — `backend/backend/services/`** и используются для двух разных задач:

1. **Chat + Vision** (`vision.py`) — уже использует OpenAI-совместимый `chat/completions` через `aiohttp`. Поддерживает оба провайдера через явный switch `_provider()` (OpenRouter имеет приоритет, OpenAI — fallback). Эта часть мигрирует тривиально: достаточно убрать ветку OpenAI.
2. **Speech-to-Text** (`voice.py`) — жёстко завязан на OpenAI Whisper (`/v1/audio/transcriptions`). **OpenRouter аудио-эндпоинт `audio/transcriptions` не предоставляет** (на момент написания у OpenRouter в API только `chat/completions` + `models`). Это блокер для прямой миграции: либо оставляем Whisper через OpenAI как «выделенное исключение для STT», либо переключаем STT на другой источник (Groq Whisper, Deepgram, локальный faster-whisper и т. п.).

Streaming, JSON mode, tool/function calling в коде **не используются** — миграция не требует переписывания промптов или парсинга ответа. Retry/backoff для LLM-запросов отсутствует (кроме telegram-отправки в worker).

**Подход:** минимально-инвазивное удаление ветки OpenAI в chat/vision и health-check; для Whisper фиксируем решение отдельным пунктом (рекомендую вариант «A» — оставить как намеренное исключение и пометить в конфиге).

## 2. Текущие LLM-вызовы

| Файл | Функция / класс | Назначение | Тип запроса |
|---|---|---|---|
| `backend/backend/services/vision.py` | `_request_chat_completion(messages, max_tokens)` | Низкоуровневый POST в `chat/completions` через `aiohttp.ClientSession` | text/vision |
| `backend/backend/services/vision.py` | `_gpt_photo(image_b64, prompt)` | Vision-запрос: одно изображение + текстовый prompt | vision |
| `backend/backend/services/vision.py` | `_gpt_text(user_text, system_prompt)` | Текстовый chat с `system`+`user` | text |
| `backend/backend/services/vision.py` | `analyze_pet_photo(image_bytes)` | Распознавание породы/возраста по фото | vision |
| `backend/backend/services/vision.py` | `analyze_food_photo(image_bytes)` | Анализ корма по фото (общий) | vision |
| `backend/backend/services/vision.py` | `analyze_food_for_pet(image_bytes, pet_info)` | Подбор питания под конкретного питомца | vision |
| `backend/backend/services/vision.py` | `consult_symptoms(symptoms_text, pet_info)` | Текстовая AI-консультация по симптомам | text |
| `backend/backend/services/vision.py` | `compare_two_foods(image1_bytes, image2_bytes)` | Сравнение двух фото кормов в одном запросе | vision |
| `backend/backend/services/vision.py` | `analyze_medical_test(image_bytes, pet_info)` | Расшифровка результатов анализов по фото | vision |
| `backend/backend/services/vision.py:338-342` | `transcribe_voice(voice_bytes)` | Прокси-врапер на `voice.transcribe_voice` | (proxy → STT) |
| `backend/backend/services/voice.py` | `transcribe_voice(voice_data)` | Распознавание голосовых OGG через OpenAI Whisper | STT (audio) |
| `backend/backend/services/provider_health.py:37-84` | `_check_ai()` | Health-check провайдера (ping `chat/completions` с `max_tokens=1`) | text |
| `backend/backend/services/provider_health.py:24-27` | `mark_ai_unavailable()` | Принудительно помечает AI как недоступный после 401/402/403 | (cache) |

**Точки входа из бота (call-sites, код не трогать):**

- `bot/bot/handlers/photo.py` — `analyze_food_for_pet`, `analyze_food_photo`, `analyze_pet_photo`, `consult_symptoms`, `transcribe_voice`
- `bot/bot/handlers/analysis.py` — `analyze_medical_test`
- `bot/bot/handlers/voice.py` — `transcribe_voice`
- `bot/bot/handlers/compare.py` — `compare_two_foods`

> Замечание: бот импортирует `backend.services.vision` **напрямую** (не через `api_client`/HTTP). Это нарушает заявленную в `docs/REFACTORING.md` границу bot↔backend, но **на эту миграцию не влияет** — публичные сигнатуры функций сохраняем как есть.

**Где НЕТ LLM-вызовов** (проверено, чтобы исключить «скрытые» места):

- `bot/bot/api_client.py` — только httpx к backend, без LLM.
- `backend/backend/services/weather.py` — wttr.in + правила, без LLM.
- `backend/backend/services/clinics.py`, `content.py`, `norms.py`, `charts.py`, `pdf_export.py`, `analytics.py`, `subscription.py`, `access.py` — без LLM.
- `worker/worker/**` — только `aiogram.Bot.send_message`, без LLM.

## 3. Модели и провайдеры

| Место в коде | Текущий провайдер | Текущая модель | Назначение | Целевая модель через OpenRouter |
|---|---|---|---|---|
| `vision.py:_request_chat_completion(for_vision=False)` (text) | OpenRouter | `OPENROUTER_MODEL=deepseek/deepseek-v4-flash` | Текстовый AI-консультант по симптомам, health-check ping | **`deepseek/deepseek-v4-flash`** — задано заказчиком (см. §9.4 итерация 3). Slug подтверждён буквально. |
| `vision.py:_request_chat_completion(for_vision=True)` (vision) | OpenRouter | `OPENROUTER_VISION_MODEL=openai/gpt-4o-mini` | Фото-сценарии: разбор питомца, корма, подбор питания, сравнение, расшифровка анализов | **`openai/gpt-4o-mini`** — большинство DeepSeek-моделей не поддерживают `image_url`, поэтому vision держим отдельной переменной с OpenAI-совместимой моделью. |
| `voice.py:transcribe_voice` (audio STT) | OpenAI (только) | `OPENAI_TRANSCRIBE_MODEL=whisper-1` | Распознавание голосовых сообщений Telegram (OGG → текст, lang=`ru`) | **❌ Нет прямого аналога в OpenRouter** — у OpenRouter в публичном API нет `audio/transcriptions`. См. §4.3 (выбор варианта). |
| `provider_health.py:_check_ai` (ping) | OpenRouter (приоритет) **или** OpenAI (fallback) | те же `OPENROUTER_MODEL` / `OPENAI_MODEL` | Health-check с `max_tokens=1` | `openai/gpt-4o-mini` (тот же, что в основном чате) |

**Параметры запроса, которые миграция должна сохранить байт-в-байт:**

- `max_tokens`: `AI_MAX_TOKENS_VISION=1600` (фото-запросы), `AI_MAX_TOKENS_TEXT=1800` (текст). Передаются в `payload["max_tokens"]`.
- `messages` schema: OpenAI-стандарт (`role`/`content` + блоки `type: image_url` / `type: text`). OpenRouter принимает их 1-в-1, переписывать не нужно.
- `detail: "high"` для image_url — поддерживается OpenRouter (форвардит upstream). Оставить как есть.
- Заголовки OpenRouter `HTTP-Referer` (`OPENROUTER_SITE_URL`) и `X-Title` (`OPENROUTER_APP_NAME`) — нужны для атрибуции в OpenRouter, оставить.
- Таймаут: `aiohttp.ClientTimeout(total=60)` для vision, `total=6` для health-check, `total=30` для Whisper — сохранить.

## 4. Что изменить

Изменения держим точечными, без рефакторинга. Все правки — только в `backend/backend/services/` и в конфиге/.env.

### 4.1 `backend/backend/services/vision.py` — убрать ветку OpenAI

Заменить switch на «только OpenRouter» при сохранении сигнатур и публичных функций.

Конкретные правки:

- **`has_any_ai()`** (строка 19-21): возвращать `bool(_settings.OPENROUTER_API_KEY)`. Убрать ссылку на `OPENAI_API_KEY`.
- **`_provider()`** (строки 24-29): удалить функцию **или** упростить до `return "openrouter" if _settings.OPENROUTER_API_KEY else None`. Если удаляем — пересмотреть тесты `TestProvider` в `test_vision.py` (см. §6).
- **`_chat_url()`** (строки 32-35): всегда `f"{_settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"`. Удалить константу `OPENAI_URL` (строка 15) или оставить как заметку — она больше не используется в коде, но импортируется тестами (см. §6).
- **`_chat_model()`** (строки 38-41): всегда `return _settings.OPENROUTER_MODEL`.
- **`_chat_headers()`** (строки 44-61): оставить только ветку `openrouter`. Если `OPENROUTER_API_KEY` пуст — `return None` (поведение сохраняется).
- Промпты (`PET_ANALYSIS_PROMPT`, `FOOD_ANALYSIS_PROMPT`, `_make_nutrition_prompt`, `_make_symptoms_prompt`, `COMPARE_PROMPT`, `MEDICAL_TEST_PROMPT`) — **не трогать**.
- Публичные функции (`analyze_pet_photo`, `analyze_food_photo`, `analyze_food_for_pet`, `consult_symptoms`, `compare_two_foods`, `analyze_medical_test`) — **не трогать сигнатуры**, они вызываются из бота.

### 4.2 `backend/backend/services/provider_health.py` — выкинуть ветку OpenAI из `_check_ai`

- **`_check_ai()`** (строки 37-84): оставить только блок `if _settings.OPENROUTER_API_KEY:` + `else: return False`. Блок `elif _settings.OPENAI_API_KEY:` (строки 53-63) — удалить.
- **`is_ai_operational()`** (строки 138-150): условие `if not _settings.OPENAI_API_KEY and not _settings.OPENROUTER_API_KEY:` (строка 143) заменить на `if not _settings.OPENROUTER_API_KEY:`.
- `mark_ai_unavailable()` не менять.

### 4.3 `backend/backend/services/voice.py` — миграция STT на OpenRouter

> **Поправка (итерация 4, 2026-05-21):** в более ранних редакциях документа я ошибочно утверждал, что OpenRouter не поддерживает `audio/transcriptions`. На самом деле эндпоинт **существует и работает**, но принимает JSON с base64-encoded аудио (не multipart, как у OpenAI напрямую). Эталонная реализация — `tarot-bot/shared/ai/engine.py:662-687`. Это позволяет довести миграцию до конца и убрать `OPENAI_*` полностью.

**Принятое решение:** `voice.py` переписан на `{OPENROUTER_BASE_URL}/audio/transcriptions`.

| Параметр | Значение |
|---|---|
| URL | `{OPENROUTER_BASE_URL}/audio/transcriptions` |
| Метод | `POST`, заголовок `Content-Type: application/json` |
| Auth | `Authorization: Bearer {OPENROUTER_API_KEY}` (+ опц. `HTTP-Referer`, `X-Title`) |
| Payload | `{"model": OPENROUTER_TRANSCRIBE_MODEL, "input_audio": {"data": <base64>, "format": "ogg"}, "language": "ru"}` |
| Slug | `openai/whisper-1` (подтверждён в проде у tarot-bot). Альтернативы: `openai/gpt-4o-transcribe`, `openai/gpt-4o-mini-transcribe` |
| Response | JSON `{"text": "..."}` (а не `text/plain`, как было у OpenAI напрямую) |

Параллельно из `Settings`/`.env.example`/`docker-compose.yml` удалены `OPENAI_API_KEY` и `OPENAI_TRANSCRIBE_MODEL` (см. §9 итерация 4).

### 4.4 Что НЕ менять

- `bot/bot/api_client.py`, `bot/bot/handlers/**` — не трогать.
- `worker/**` — там нет LLM-вызовов.
- Промпты — оставить как есть. Они не содержат фишек, специфичных для OpenAI.
- Сигнатуры публичных функций vision — сохранить.
- `subprocess` / `alembic` / lifespan FastAPI — не трогать.
- Зависимости `pyproject.toml`: `aiohttp` уже стоит; **новые пакеты не добавляем**, SDK `openai`/`anthropic` в проект не тянем.

## 5. Config / env / deploy

### 5.1 `shared/zoo_shared/config.py`

Если выбран **вариант A** (см. §4.3) — структуру `Settings` оставляем как есть: и `OPENAI_API_KEY`, и `OPENROUTER_*` нужны (первый — для Whisper, остальные — для chat/vision).

Если выбран вариант **B** или **C** — удалить из `Settings`:
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_TRANSCRIBE_MODEL`

…и поправить тест `shared/tests/test_config.py:18` (см. §6).

### 5.2 `.env.example`

Для варианта A — переписать комментарии секции `AI PROVIDERS` так, чтобы было видно «кто за что отвечает»:

```env
# ══════ AI PROVIDERS ══════
# OpenRouter — chat + vision (требуется)
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_SITE_URL=
OPENROUTER_APP_NAME=zoo_bot

# OpenAI — нужен только для распознавания голоса (Whisper).
# Оставить пустым, если STT отключён.
OPENAI_API_KEY=
OPENAI_TRANSCRIBE_MODEL=whisper-1
# OPENAI_MODEL больше не используется (chat ушёл в OpenRouter)
```

Для вариантов B/C — удалить из `.env.example` все `OPENAI_*` строки.

### 5.3 `docker-compose.yml`

В сервисах `backend` и `bot` (строки 53-60, 91-100):

- **Удалить** проброс `OPENAI_MODEL` — он больше не читается кодом.
- **Оставить** `OPENAI_API_KEY` и `OPENAI_TRANSCRIBE_MODEL` (вариант A) — нужны Whisper.
- **Оставить** все `OPENROUTER_*` переменные.

Сервис `migrate` LLM не использует — не трогать.

### 5.4 README / docs

- `README.md`: если есть упоминания AI-провайдеров (сейчас нет напрямую) — обновить. Достаточно одной строки в разделе «Переменные окружения»: *«Для chat/vision требуется `OPENROUTER_API_KEY`. `OPENAI_API_KEY` нужен только для распознавания голоса.»*
- `docs/REFACTORING.md` — не трогать (это исторический документ, отражает прошлое состояние).
- `docs/LLM_PROVIDER_MIGRATION.md` — этот файл.

### 5.5 Production secrets

На VPS (`/opt/zoo_bot/.env`) проверить, что задан `OPENROUTER_API_KEY` (если уже работает — проверить через `docker compose exec backend env | grep OPENROUTER`). Если выбран вариант A — также убедиться, что `OPENAI_API_KEY` присутствует, иначе голосовой ввод сломается. В GitHub Actions secrets (если ключи приходят через них) — добавить/удалить переменные синхронно.

## 6. Тесты

### 6.1 Тесты, которые СЛОМАЮТСЯ и должны быть обновлены

| Файл | Что сломается | Что сделать |
|---|---|---|
| `backend/tests/test_vision.py` | `OPENAI_URL` импортируется (строка 12, 64, 74, 151); `_provider()` тесты `test_openrouter_wins`, `test_openai_fallback`, `test_none_when_no_keys`; `test_openai_url_fallback`, `test_openai_model_fallback`, `test_openai_headers` — все они подтверждают наличие OpenAI-ветки | Удалить эти подтесты или превратить в тест «при пустом OPENROUTER → `_chat_headers()` is None». Оставить тесты, проверяющие OpenRouter (URL, model, headers, `HTTP-Referer`, `X-Title`). Промпт-тесты не трогать. |
| `backend/tests/test_vision.py:172-173` фикстура `no_ai_keys` | Сейчас сетит и `OPENROUTER_API_KEY=""`, и `OPENAI_API_KEY=""` | Достаточно сетить только `OPENROUTER_API_KEY=""` |
| `shared/tests/test_config.py:18` | `assert s.OPENAI_MODEL == "gpt-4o-mini"` | Вариант A: оставить. Вариант B/C: удалить assertion и/или заменить на `OPENROUTER_MODEL == "openai/gpt-4o-mini"` |

### 6.2 Тесты, которые ОСТАЮТСЯ как есть (вариант A)

- `backend/tests/test_voice.py` — Whisper остаётся на OpenAI, тесты не меняются.
- `backend/tests/test_provider_health.py` — проверяет только кеш-логику, не делает реальный HTTP-запрос. Просто проверить, что после правки в `_check_ai()` ничего не падает по импорту.

### 6.3 Тесты, которые НУЖНО ДОБАВИТЬ

В `backend/tests/test_vision.py` добавить класс `TestOpenRouterOnly` (или дополнить существующие):

1. **`test_request_uses_openrouter_url_and_model`** — замокать `aiohttp.ClientSession.post`, проверить, что фактический URL содержит `openrouter.ai` и payload содержит `model == OPENROUTER_MODEL`. Достаточно одного теста с фейковым 200-ответом.
2. **`test_openrouter_headers_attached`** — проверить, что в запрос идут `Authorization: Bearer <OPENROUTER_API_KEY>`, `HTTP-Referer`, `X-Title` (если заданы).
3. **`test_no_openrouter_key_returns_none`** — без ключа `_request_chat_completion` отдаёт `None`, не делая HTTP-вызова.
4. **`test_http_401_marks_ai_unavailable`** — мок-резп со статусом 401; проверить, что `mark_ai_unavailable()` сработала (через `_CACHE["ai"]["status"] is False`).
5. **`test_http_5xx_returns_none_without_marking`** — мок-резп 500; проверить, что `mark_ai_unavailable` НЕ вызвана.
6. **`test_timeout_returns_none`** — `aiohttp.ClientSession.post` бросает `asyncio.TimeoutError`; функция возвращает `None`, без исключения наружу.
7. **`test_no_openai_url_anywhere`** (статический guard) — `assert "api.openai.com" not in vision_mod._chat_url()` для всех валидных конфигов. Можно использовать `grep`-проверку в CI или просто прочитать модуль через `inspect.getsource`.

В `backend/tests/test_provider_health.py` добавить:

1. **`test_check_ai_uses_openrouter_url`** — при `OPENROUTER_API_KEY="x"` мок-`aiohttp.ClientSession` ловит URL, проверить, что в нём `openrouter.ai`.
2. **`test_check_ai_returns_false_without_openrouter_key`** — без ключа сразу `False`, без HTTP.

### 6.4 Ручной smoke-test (acceptance, см. §8)

Запустить `docker compose up -d` с заполненным `OPENROUTER_API_KEY`, написать боту через Telegram:

1. `/start` → отправить фото питомца в раздел «Фото-анализ» → ожидаем ответ от LLM (русский, с эмодзи, длиннее 100 символов).
2. AI-консультант → отправить текстовый симптом → ожидаем ответ.
3. Сравнение кормов → два фото → ожидаем ответ.
4. AI-анализ медицинских анализов → фото с цифрами → ожидаем ответ.
5. Голосовое (если вариант A): записать «привет» → ожидаем транскрипцию (этот шаг идёт через OpenAI Whisper, не через OpenRouter — это ожидаемо).
6. В логах backend: `grep -i "openrouter.ai" logs` показывает HTTP-вызовы; `grep -i "api.openai.com/v1/chat" logs` — пусто (кроме `audio/transcriptions` для Whisper).

## 7. Риски

| # | Риск | Влияние | Митигация |
|---|---|---|---|
| 1 | **Whisper не доступен через OpenRouter** | STT сломается, если не оставить OpenAI ключ | Вариант A: оставить `OPENAI_API_KEY` только для Whisper (§4.3). Прописать это в README/.env, иначе деплой будет неполным. |
| 2 | **Модель в OpenRouter переименовалась / снята** | Запросы начнут возвращать 404, AI помечается недоступным | Прибить дефолт в `.env.example` к стабильному id (`openai/gpt-4o-mini`), и/или добавить алерт в логах при `mark_ai_unavailable`. Перед мерджем — проверить slug в каталоге OpenRouter. |
| 3 | **Расхождения форматов ответа** между моделями (особенно если выберут не `openai/*`, а `anthropic/*` или `google/*`) | Vision-блоки `image_url` обрабатываются по-разному; `system` у Claude трактуется отдельным полем (OpenRouter сам нормализует, но не всегда идеально) | Зафиксировать дефолт `openai/gpt-4o-mini` через OpenRouter и НЕ менять в этой миграции. Любая смена модели — отдельная задача с регресс-тестом. |
| 4 | **Стоимость / latency** | OpenRouter добавляет ~50-150 мс latency vs прямой OpenAI; цена на ту же модель чуть выше | Принимаемо для текущих нагрузок. Если станет проблемой — рассмотреть прямой fallback в будущем. |
| 5 | **Streaming не используется сейчас, но если внезапно потребуется** | OpenRouter поддерживает SSE так же, как OpenAI | Не входит в эту миграцию; если будет добавляться — отдельным PR. |
| 6 | **JSON / tool calling** | Не используется → не блокер. Если в будущем понадобится — у OpenRouter `response_format` и `tools` поддерживаются для большинства моделей (но не для всех). | Зафиксировать в архитектурном решении; пока ничего не делать. |
| 7 | **Скрытые LLM-вызовы** | В коде есть `from backend.services.vision import transcribe_voice` — это **прокси** на `voice.transcribe_voice`, не отдельный LLM-вызов. Других «скрытых» интеграций нет. | Перепроверено `grep -rn "openai\|whisper\|gpt-\|anthropic"` — лишних вызовов нет. |
| 8 | **Старые env-переменные остаются на проде** | После выкатки в `/opt/zoo_bot/.env` останется `OPENAI_MODEL=gpt-4o-mini`, который больше не читается — мёртвая переменная | Не критично (никто не падает). Опционально: добавить заметку «удалить после миграции» в release-notes. |
| 9 | **Кэш `_CACHE["ai"]` может «прилипнуть» в `False`** после первого 401, и до 10 минут блокировать запросы | Если правка `_check_ai()` оставит баг — все AI-сценарии отвалятся на 10 минут | После релиза вручную проверить `GET /services/health/ai`, дернуть `refresh_provider_health(force=True)` через тест или рестарт контейнера backend. |
| 10 | **Бот ходит в `backend.services.vision` напрямую (не через httpx)** | Не относится к миграции, но усиливает связность. Если миграция случайно изменит сигнатуру публичной функции — упадёт бот | Сигнатуры публичных функций жёстко зафиксированы в §4.1 как неизменные. |

## 8. Acceptance criteria

Миграция считается завершённой, если выполнены **все** пункты:

- [ ] В `backend/backend/services/vision.py` функции `_provider`, `_chat_url`, `_chat_model`, `_chat_headers` либо удалены, либо упрощены до одной ветки OpenRouter; `OPENAI_URL` больше не используется в продакшен-коде.
- [ ] В `backend/backend/services/provider_health.py:_check_ai` нет ветки `elif _settings.OPENAI_API_KEY`.
- [ ] `grep -rn "api.openai.com/v1/chat" backend/backend bot worker` возвращает **0 совпадений** (только в тестах допускается, и только как guard-asserts).
- [ ] Все vision-сценарии (фото питомца, фото корма, подбор питания, симптомы, сравнение, мед. анализы) проходят ручной smoke-test через Telegram-бота и реально дергают `openrouter.ai` (видно в логах backend).
- [ ] Health-check `GET /services/health/ai` возвращает `{"operational": true}` при заполненном `OPENROUTER_API_KEY` и `{"operational": false}` при пустом.
- [ ] (Вариант A) Голосовой ввод продолжает работать через OpenAI Whisper; это явно задокументировано в `.env.example` и README. ИЛИ (вариант B/C) — STT отключен/мигрирован по отдельному ТЗ.
- [ ] `pyproject.toml` сервисов не получил новых зависимостей (OpenAI SDK / Anthropic SDK не подтягиваются).
- [ ] `pytest --cov-fail-under=75` проходит после правки тестов; новые тесты из §6.3 включены.
- [ ] `ruff check .` проходит.
- [ ] `.env.example` и `docker-compose.yml` синхронизированы по списку переменных; в README одна актуальная строка про распределение ключей.
- [ ] CI-пайплайн зелёный; CD-деплой на VPS успешен; на проде в `.env` присутствует `OPENROUTER_API_KEY` (и `OPENAI_API_KEY`, если вариант A).

---

## 9. Доработка (по итогам код-ревью, обновлено после итерации 3)

### Итерация 3 (2026-05-20): split text/vision моделей по требованию заказчика

Заказчик зафиксировал основную текстовую модель — **`deepseek/deepseek-v4-flash`**. Так как большинство DeepSeek-моделей в OpenRouter не поддерживают `image_url` (vision), модель пришлось развести на две переменные.

**Изменения в коде:**

| Файл | Изменение |
|---|---|
| `shared/zoo_shared/config.py` | Добавлено поле `OPENROUTER_VISION_MODEL: str = "openai/gpt-4o-mini"`. Дефолт `OPENROUTER_MODEL` изменён на `deepseek/deepseek-v4-flash`. |
| `backend/backend/services/vision.py` | `_chat_model(for_vision: bool = False)` теперь возвращает либо `OPENROUTER_MODEL` (текст), либо `OPENROUTER_VISION_MODEL` (фото). `_request_chat_completion` принимает `for_vision`. `_gpt_photo` и `compare_two_foods` передают `for_vision=True`; `_gpt_text` — `False` (по умолчанию). |
| `backend/backend/services/provider_health.py` | Не тронут: ping `_check_ai` использует `OPENROUTER_MODEL` (текстовая) — это намеренно, чтобы health-check проверял именно ту модель, через которую пойдут текстовые запросы. |
| `.env.example` | Добавлен `OPENROUTER_VISION_MODEL=openai/gpt-4o-mini`. `OPENROUTER_MODEL` приведён к `deepseek/deepseek-v4-flash`. Добавлены комментарии о разделении ролей. |
| `docker-compose.yml` | В `backend` и `bot` проброс `OPENROUTER_VISION_MODEL` и обновлён дефолт `OPENROUTER_MODEL`. |
| `shared/tests/test_config.py` | Обновлён assert: `OPENROUTER_MODEL == "deepseek/deepseek-v4-flash"`, добавлен `OPENROUTER_VISION_MODEL == "openai/gpt-4o-mini"`. |
| `backend/tests/test_vision.py` | Добавлен `test_text_and_vision_models_split` (юнит-тест на `_chat_model(for_vision=)`). Добавлены два интеграционных теста с замоканным `aiohttp.ClientSession`: `test_gpt_photo_uses_vision_model` (фото → `openai/gpt-4o-mini`) и `test_gpt_text_uses_text_model` (текст → `deepseek/deepseek-v4-flash`). |

**Публичные сигнатуры функций vision НЕ изменены** — `analyze_pet_photo`, `analyze_food_for_pet`, `consult_symptoms`, `compare_two_foods`, `analyze_medical_test` принимают те же аргументы; бот-handlers не меняются.

**Что нужно дополнительно проверить кодеру в smoke-test (§9.2.2):**

1. Slug `deepseek/deepseek-v4-flash` действительно существует в каталоге OpenRouter — если slug опечатан/неактивен, на любой текстовый запрос (например, AI-консультант по симптомам) придёт 404 → AI помечается недоступным. В этом случае подобрать актуальный slug DeepSeek на https://openrouter.ai/models и обновить дефолт.
2. Фото-сценарии работают (используют `openai/gpt-4o-mini`) — это известно работающее сочетание.
3. Health-check `/services/health/ai` корректно проверяет именно текстовую модель.

**⚠ Связанный риск:** `is_ai_operational()` сейчас пингует только **текстовую** модель (`OPENROUTER_MODEL`), но в боте (`bot/handlers/photo.py`, `analysis.py`, `compare.py` — 16 точек проверки) этот же флаг гейтит ВСЕ AI-сценарии, включая фото. Если slug `deepseek/deepseek-v4-flash` окажется битый, **фото-сценарии тоже отключатся ложно**, хотя `OPENROUTER_VISION_MODEL=openai/gpt-4o-mini` сам по себе рабочий. Если это станет проблемой — отдельной задачей развести health-check на два пинга (текст и vision) и пробросить два флага в бот. В рамках текущей миграции трогать не стоит — это уже архитектурное изменение API.

---



Дата последнего ревью: 2026-05-20. Проверены диффы в:
- `backend/backend/services/vision.py`
- `backend/backend/services/provider_health.py`
- `backend/tests/test_vision.py`
- `backend/tests/test_provider_health.py`
- `shared/zoo_shared/config.py`
- `shared/tests/test_config.py`
- `.env.example`
- `docker-compose.yml`
- `README.md`

### 9.1 Что закрыто корректно ✅

| Пункт | Файл / место | Статус |
|---|---|---|
| Удалена ветка OpenAI в chat/vision | `vision.py`: `has_any_ai/_provider/_chat_url/_chat_model/_chat_headers` работают только с `OPENROUTER_*`; константа `OPENAI_URL` удалена | OK |
| Сохранены публичные сигнатуры | `analyze_pet_photo`, `analyze_food_photo`, `analyze_food_for_pet`, `consult_symptoms`, `compare_two_foods`, `analyze_medical_test`, `transcribe_voice` (proxy) — на месте | OK |
| Промпты не тронуты | `PET_ANALYSIS_PROMPT`, `FOOD_ANALYSIS_PROMPT`, `COMPARE_PROMPT`, `MEDICAL_TEST_PROMPT`, `_make_nutrition_prompt`, `_make_symptoms_prompt` — без изменений | OK |
| Удалена ветка OpenAI в health-check | `provider_health.py:_check_ai` — только OpenRouter; `is_ai_operational` проверяет только `OPENROUTER_API_KEY` | OK |
| Whisper-вариант A зафиксирован | `voice.py` не изменён; `vision.py:transcribe_voice` — прокси на `voice.transcribe_voice`. В docstring `vision.py` и `config.py:22` явно отмечено «нужен только для Whisper STT» | OK |
| `.env.example` пересобран | OpenRouter блок первым (chat+vision required), OpenAI ниже с пометкой «ТОЛЬКО для Whisper»; устаревший комментарий про `OPENAI_MODEL` тоже убран | OK |
| `docker-compose.yml` синхронизирован | Из `backend` и `bot` удалён `OPENAI_MODEL`; `OPENAI_API_KEY` и `OPENAI_TRANSCRIBE_MODEL` оставлены | OK |
| Тесты `test_vision.py` | Импорт `OPENAI_URL` удалён; OpenAI-asserts вычищены; добавлен `TestOpenRouterOnly` (7 сценариев §6.3); фикстура `no_ai_keys` упрощена до одной переменной | OK |
| Тесты `test_provider_health.py` | Добавлен `TestCheckAiOpenRouterOnly` с двумя сценариями (no-key → False; uses openrouter.ai URL) | OK |
| README обновлён (итерация 2) | `README.md:119-121` — добавлена секция «Опциональные (для AI-функций)» с описанием ролей `OPENROUTER_API_KEY` и `OPENAI_API_KEY` | OK |
| Мёртвое поле `OPENAI_MODEL` удалено (итерация 2) | `shared/zoo_shared/config.py` — поле удалено; `shared/tests/test_config.py:18` — assertion заменён на `OPENROUTER_MODEL == "openai/gpt-4o-mini"`; `.env.example` — комментарий-deprecation удалён | OK |
| Зависимости не выросли | `backend/pyproject.toml` не менялся; SDK `openai`/`anthropic` не подтянуты | OK |

**Статические guard-проверки** (выполнены grep'ом по продакшен-коду, исключая `docs/` и тесты):

- `grep -rn "api.openai.com/v1/chat" backend bot worker shared` → **0 совпадений**.
- `grep -rn "OPENAI_MODEL" backend bot worker shared` → **0 совпадений** (поле полностью вычищено из кода, тестов и `.env.example`).
- `grep -rn "api.openai.com" backend bot worker shared` → одно ожидаемое совпадение в `voice.py:12` (`WHISPER_URL` — вариант A для Whisper) + один guard-assert в `test_vision.py:195`.

### 9.2 Что осталось закрыть (runtime-проверки) ⚠️

Эти пункты невозможно выполнить из кода/ревью статически — их должен закрыть кодер на своём окружении / в CI.

#### 9.2.1 Прогон `pytest` и `ruff`

Локально в окружении ревью `pytest` не установлен — проверить нельзя. Кодер должен запустить:

```bash
pytest --cov=backend --cov=shared --cov=bot --cov=worker \
       --cov-report=term-missing --cov-fail-under=75
ruff check .
```

Точки риска, на которые обратить внимание в выводе:
- Новые тесты в `TestOpenRouterOnly` мокают `aiohttp.ClientSession` через `monkeypatch.setattr(vision_mod.aiohttp, "ClientSession", lambda: _Sess())`. Подмена идёт через атрибут модуля — это работает только потому, что `vision.py:10` импортирует `import aiohttp`. Если внезапно появится `from aiohttp import ClientSession` — моки сломаются.
- `test_http_401_marks_ai_unavailable` и `test_http_5xx_returns_none_without_marking` модифицируют глобальный `ph._CACHE["ai"]["status"]`. При параллельном прогоне тестов (если в CI `pytest-xdist`) может ловиться race; сейчас в проекте `xdist` не используется — риск низкий, но если будет — потребуется autouse-fixture с reset кэша.
- `ruff` в проекте сконфигурирован через корневой `pyproject.toml`. Новые тесты содержат много `_Resp`/`_Sess` стаб-классов в одну строку — это стилистически может вызвать предупреждение, но не ошибку (E501/E701).

#### 9.2.2 Ручной smoke-test (ТЗ §6.4)

Запустить локально или на dev/staging:

1. В `.env`: `OPENROUTER_API_KEY=sk-or-...`, `OPENROUTER_MODEL=openai/gpt-4o-mini`. Опционально `OPENAI_API_KEY=sk-...` (для Whisper).
2. `docker compose up -d --build`.
3. `curl http://localhost:8000/services/health/ai` → `{"operational": true}` при заполненном ключе; `{"operational": false}` при пустом.
4. В Telegram: фото питомца → ожидаем разбор от LLM.
5. AI-консультант: текст «у кота кашель третий день» → ожидаем ответ.
6. Сравнение двух кормов: два фото → ожидаем сравнительный ответ.
7. Голосовое сообщение → транскрипция через OpenAI Whisper (это ожидаемое исключение для STT).
8. `docker compose logs backend | grep -i openrouter.ai` показывает реальные HTTP-вызовы; `grep "api.openai.com/v1/chat"` — пусто.

#### 9.2.3 Прод-окружение

После деплоя проверить на VPS:

```bash
docker compose exec backend env | grep -E 'OPENROUTER|OPENAI'
```

Ожидаем: `OPENROUTER_API_KEY` установлен (непустой). `OPENAI_MODEL` не передаётся через compose-файл (уже удалено) — если осталось в самом `/opt/zoo_bot/.env`, переменная безвредна (`Settings` её игнорирует через `extra="ignore"`), но почистить её при следующей правке `.env` — желательно.

### 9.3 Минорные косметические замечания (не блокеры)

- `docs/REFACTORING.md` и `docs/bug_report.md` содержат снимки старого кода (двойная проверка `OPENAI_API_KEY or OPENROUTER_API_KEY`, дефолт `OPENAI_MODEL=gpt-4o-mini`). Это исторические документы — не трогаем; при желании добавить в шапку каждого пометку «снимок до миграции OpenRouter, актуальное состояние — `docs/LLM_PROVIDER_MIGRATION.md`».
- `backend/tests/test_voice.py:29-35` — тест `test_no_api_key_returns_none` использует условный assertion (`if not settings.OPENAI_API_KEY:`), что в CI с заполненным ключом превращается в no-op. Это существовало ДО миграции и не входит в её скоуп.

### 9.4 Финальный чек-лист

**Закрыто (итерации 1 → 4):**

- [x] Удалена ветка OpenAI из `vision.py` и `provider_health.py` (итер. 1).
- [x] Мёртвое поле `OPENAI_MODEL` удалено из `Settings`, теста и `.env.example` (итер. 2).
- [x] Разделены текстовая и vision модели: `OPENROUTER_MODEL=deepseek/deepseek-v4-flash`, `OPENROUTER_VISION_MODEL=openai/gpt-4o-mini` (итер. 3).
- [x] **STT перенесён на OpenRouter** `/audio/transcriptions`; `OPENAI_API_KEY` и `OPENAI_TRANSCRIBE_MODEL` полностью удалены из кода/конфига; добавлен `OPENROUTER_TRANSCRIBE_MODEL=openai/whisper-1` (итер. 4).
- [x] `test_voice.py` переписан под новый payload (JSON + base64); добавлен payload-assertion-тест.
- [x] `.env.example`, `docker-compose.yml`, README синхронизированы.
- [x] Новых зависимостей не добавлено (`aiohttp` и `base64` — стандартный стек).

**Остаётся на стороне кодера / CI / прода:**

- [ ] Прогнать `pytest --cov-fail-under=75` и `ruff check .` — приложить вывод к PR (§9.2.1).
- [ ] Выполнить ручной smoke-test §9.2.2 на dev или staging (включая голосовое сообщение — оно теперь идёт через OpenRouter).
- [ ] После деплоя — убедиться, что `OPENROUTER_API_KEY` в проде непустой; удалить мёртвые `OPENAI_API_KEY`/`OPENAI_TRANSCRIBE_MODEL` из `/opt/zoo_bot/.env` (опционально — `extra="ignore"` их игнорирует, но это мусор).

После закрытия §9.4 миграция считается **полностью завершённой**; пункты §8 можно отмечать.

---

### Итерация 4 (2026-05-21): полный перенос STT на OpenRouter

**Триггер:** заказчик уточнил, что OpenRouter поддерживает `/audio/transcriptions` (`https://openrouter.ai/models?output_modalities=transcription`). Прежнее утверждение в §4.3 было неверным.

**Что изменилось:**

| Файл | Правка |
|---|---|
| `shared/zoo_shared/config.py` | Удалены `OPENAI_API_KEY` и `OPENAI_TRANSCRIBE_MODEL`. Добавлено `OPENROUTER_TRANSCRIBE_MODEL: str = "openai/whisper-1"`. |
| `backend/backend/services/voice.py` | Переписан: URL → `{OPENROUTER_BASE_URL}/audio/transcriptions`, JSON-body c `input_audio.data` (base64) и `format: "ogg"`, ответ парсится через `.json()["text"]`. Используется `OPENROUTER_API_KEY` + опц. `HTTP-Referer`/`X-Title`. |
| `.env.example` | Удалена секция OpenAI. Добавлено `OPENROUTER_TRANSCRIBE_MODEL=openai/whisper-1` с комментарием про альтернативы. |
| `docker-compose.yml` | Из `backend` и `bot` удалены `OPENAI_API_KEY` и `OPENAI_TRANSCRIBE_MODEL`. Добавлено `OPENROUTER_TRANSCRIBE_MODEL`. |
| `README.md` | Список ENV: `OPENROUTER_API_KEY` теперь покрывает в том числе транскрипцию; упоминание `OPENAI_API_KEY` удалено. |
| `shared/tests/test_config.py` | Добавлен `assert s.OPENROUTER_TRANSCRIBE_MODEL == "openai/whisper-1"`. |
| `backend/tests/test_voice.py` | Полностью переписан: проверка URL (`openrouter.ai`), отсутствия `api.openai.com`, формирование заголовков, успех/ошибка/таймаут/пустой текст. Добавлен `test_payload_uses_base64_and_configured_model` — фиксирует структуру JSON-payload (model, base64, format=ogg, language=ru). |
| `docs/LLM_PROVIDER_MIGRATION.md` (§4.3) | Сделана поправка с явным указанием, что прежнее утверждение «OpenRouter не поддерживает audio/transcriptions» было ошибочным; добавлена эталонная ссылка на `tarot-bot/shared/ai/engine.py:662`. |

**Эталонная реализация:** `/Users/core/code/WB/tarot-bot/shared/ai/engine.py:662-687` (`transcribe_voice`). Используется тот же контракт: `httpx`→`aiohttp` — единственное технологическое отличие (в zoo единый стек на `aiohttp`).

**Проверка чистоты:**
- `grep -rn "OPENAI_API_KEY\|OPENAI_TRANSCRIBE_MODEL\|api.openai.com" backend bot worker shared` → **0 совпадений** в живом коде/конфигах.
- `grep -rn "api.openai.com" backend bot worker shared` → совпадения остаются только в `docs/REFACTORING.md`, `docs/bug_report.md` (исторические снимки) и в guard-assert тесте `test_vision.py:202` (`assert "api.openai.com" not in _chat_url()`).

**Slug `openai/whisper-1`** подтверждён рабочим у tarot-bot в проде; smoke-test голосового сценария — обязательная часть приёмки итерации.
