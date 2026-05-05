# ZooBuddy — План рефакторинга

---

## §1. Текущее состояние

### 1.1 Кодовая база

| Метрика | Значение |
|---------|----------|
| Всего Python-кода | **~10 114 LOC** в 45 файлах |
| Самые толстые файлы | `handlers/pets.py` (907), `handlers/payment.py` (845), `handlers/food.py` (796), `handlers/medical.py` (752), `handlers/photo.py` (740) |
| Модели | 14 таблиц в одном `models/models.py` (262 LOC) |
| Тестов | **0** |

### 1.2 Архитектура (as-is)

```
bot.py (entrypoint — polling)
  ├─ config.py           — os.getenv, всё в глобальных переменных
  ├─ database.py         — SQLAlchemy engine + async_session + init_db()
  │                        (create_all + ручные ALTER TABLE миграции)
  ├─ handlers/ (17 роутеров)
  │    └─ каждый handler напрямую делает `async with async_session()`
  │       → SELECT / INSERT / UPDATE прямо в хендлере
  ├─ services/
  │    ├─ scheduler.py   — APScheduler в том же процессе + global _bot
  │    ├─ vision.py      — aiohttp → OpenRouter/OpenAI
  │    ├─ voice.py       — aiohttp → Whisper
  │    ├─ weather.py     — aiohttp → wttr.in
  │    ├─ clinics.py     — aiohttp → Overpass API
  │    ├─ subscription.py — проверки лимитов (ходит в БД)
  │    ├─ payment … analytics … charts … pdf_export …
  │    └─ provider_health.py — health-check AI + YooKassa
  ├─ keyboards/          — один файл 381 LOC
  ├─ models/models.py    — все 14 моделей
  ├─ states/states.py    — все FSM-группы
  ├─ middlewares/         — ErrorGuard + Throttle
  └─ utils/helpers.py    — парсинг дат/весов
```

### 1.3 Ключевые проблемы

| # | Проблема | Риск |
|---|----------|------|
| 1 | **Монолит**: бот, планировщик, платёжный поллинг — в одном процессе | Если scheduler зависает — polling падает |
| 2 | **БД через create_all**: ручные ALTER TABLE в `_ensure_schema` | Невоспроизводимые миграции, рассинхрон |
| 3 | **Handlers → DB напрямую**: нет API-слоя | Невозможно масштабировать/переиспользовать |
| 4 | **SQLite в проде** (default) | Один writer, нет concurrent access |
| 5 | **Global `_bot`** в scheduler | Worker-паттерн невозможен |
| 6 | **Нет тестов** | 0% coverage |
| 7 | **Деплой**: rsync + systemd, без контейнеризации | Drift конфигурации, нет версионирования |
| 8 | **Нет .gitignore** (был только .env.example) | Логи, __pycache__, .db могли попадать в репо |
| 9 | **Толстые handlers** (pets 907, payment 845) | Сложно читать, тестировать |
| 10 | **config.py** — `load_dotenv()` при импорте | Не работает в мультисервисной архитектуре |

### 1.4 Инфраструктура (as-is)

- **Прод-хост**: Ubuntu VPS, Python 3.11+, systemd unit `zoo_bot.service`
- **БД**: SQLite (default) / Postgres готов через `DATABASE_URL`
- **FSM Storage**: MemoryStorage (default) / Redis (optional)
- **Платежи**: YooKassa (карта) + Telegram Stars
- **AI**: OpenRouter / OpenAI (vision, whisper, text)
- **Внешние API**: wttr.in (погода), Overpass (клиники)
- **Деплой**: `deploy.sh` → rsync → `systemctl restart zoo_bot`

---

## §2. Предлагаемый состав сервисов

### Вариант: 5 контейнеров (bot + backend + worker + postgres + redis)

| Сервис | Зона ответственности | Почему отдельный |
|--------|---------------------|-----------------|
| **bot** | aiogram Dispatcher, polling/webhook, FSM, handlers. Не ходит в БД напрямую — через httpx → backend | Изоляция Telegram I/O; при крэше бота worker продолжает работу |
| **backend** | FastAPI. REST API для CRUD (pets, reminders, medical, food, payments, subscriptions, analytics). Alembic в entrypoint | Единая точка доступа к БД; переиспользуемый API для будущих клиентов (web, mobile) |
| **worker** | APScheduler + фоновые задачи (напоминания, vaccination check, weather notifications, payment reconciliation). Пишет/читает БД напрямую через shared/db. Отправляет Telegram через `Bot(token)` singleton | Тяжёлые/периодические задачи не блокируют polling |
| **postgres** | PostgreSQL 16 | Замена SQLite; concurrent access, полноценные миграции |
| **redis** | FSM storage + кэш (provider health, rate limits) | Персистентный FSM между рестартами бота; готовность к горизонтальному масштабированию |

**Обоснование максимального варианта (5 контейнеров):**
- Бот сейчас совмещает I/O-bound (polling) и CPU-bound (charts, pdf, AI-запросы) + cron-задачи. Разделение на bot/backend/worker даёт fault-isolation и независимый рестарт.
- Backend как отдельный сервис позволяет в будущем добавить webhook-режим, web-панель, mobile API — без изменения bot-кода.
- Worker с прямым доступом к БД (через shared/db) избегает HTTP-хопа для массовых cron-операций (сканирование всех прививок, рассылка погоды).

### Коммуникация между сервисами

```
┌──────────┐   httpx    ┌──────────┐   asyncpg   ┌──────────┐
│   bot    │──────────→ │ backend  │────────────→ │ postgres │
└──────────┘            └──────────┘              └──────────┘
                              ↑                        ↑
                              │ alembic (entrypoint)   │
                              │                        │
┌──────────┐   shared/db (asyncpg, напрямую)          │
│  worker  │──────────────────────────────────────────┘
└──────────┘
      │ Bot(token) → Telegram API  (output-only)
      │
      ↕
┌──────────┐
│  redis   │ ← FSM storage (bot) + кэш (backend/worker)
└──────────┘
```

---

## §3. Целевая структура каталогов

```
zoo/
├── .github/
│   └── workflows/
│       └── deploy.yml              # CD: push main → build → deploy
│
├── docker/
│   ├── bot.Dockerfile
│   ├── backend.Dockerfile
│   └── worker.Dockerfile
│
├── shared/                          # Общий код (pip install -e . в каждом контейнере)
│   ├── pyproject.toml               # пакет "zoo_shared"
│   └── zoo_shared/
│       ├── __init__.py
│       ├── config.py                # Pydantic Settings (одна точка конфигурации)
│       ├── db/
│       │   ├── __init__.py
│       │   ├── engine.py            # create_async_engine + sessionmaker
│       │   └── models.py            # все SQLAlchemy-модели
│       └── schemas/                 # Pydantic-схемы (shared между bot↔backend)
│           ├── __init__.py
│           ├── pet.py
│           ├── reminder.py
│           ├── medical.py
│           ├── food.py
│           ├── subscription.py
│           ├── payment.py
│           └── analytics.py
│
├── alembic/                         # Миграции (запускается в backend entrypoint)
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│       └── 001_initial.py
│
├── bot/                             # Сервис: Telegram-бот
│   ├── pyproject.toml
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── main.py                  # entrypoint (Dispatcher + polling)
│   │   ├── api_client.py            # httpx-клиент к backend
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   ├── common.py
│   │   │   ├── pets.py
│   │   │   ├── reminders.py
│   │   │   ├── medical.py
│   │   │   ├── food.py
│   │   │   ├── tips.py
│   │   │   ├── emergency.py
│   │   │   ├── photo.py
│   │   │   ├── norms.py
│   │   │   ├── compare.py
│   │   │   ├── voice.py
│   │   │   ├── calendar_view.py
│   │   │   ├── weight_goal.py
│   │   │   ├── subscription.py
│   │   │   ├── payment.py
│   │   │   ├── weather_handler.py
│   │   │   └── analysis.py
│   │   ├── keyboards/
│   │   │   ├── __init__.py
│   │   │   └── keyboards.py
│   │   ├── states/
│   │   │   ├── __init__.py
│   │   │   └── states.py
│   │   ├── middlewares/
│   │   │   ├── __init__.py
│   │   │   ├── error_guard.py
│   │   │   └── throttle.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── helpers.py
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       └── ...
│
├── backend/                         # Сервис: FastAPI REST API
│   ├── pyproject.toml
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app + lifespan (alembic upgrade head)
│   │   ├── deps.py                  # get_session dependency
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── pets.py
│   │   │   ├── reminders.py
│   │   │   ├── medical.py
│   │   │   ├── food.py
│   │   │   ├── subscriptions.py
│   │   │   ├── payments.py
│   │   │   ├── analytics.py
│   │   │   └── health.py            # readiness/liveness + provider health
│   │   └── services/                # Бизнес-логика (перенесена из services/)
│   │       ├── __init__.py
│   │       ├── subscription.py
│   │       ├── vision.py
│   │       ├── voice.py
│   │       ├── weather.py
│   │       ├── clinics.py
│   │       ├── charts.py
│   │       ├── norms.py
│   │       ├── pdf_export.py
│   │       ├── content.py
│   │       ├── analytics.py
│   │       └── provider_health.py
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       └── ...
│
├── worker/                          # Сервис: фоновые задачи
│   ├── pyproject.toml
│   ├── worker/
│   │   ├── __init__.py
│   │   ├── main.py                  # entrypoint: APScheduler + Bot singleton
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── reminders.py         # send_reminder, load_all_reminders
│   │   │   ├── vaccinations.py      # check_vaccination_schedule
│   │   │   ├── weather.py           # send_weather_notifications
│   │   │   ├── payments.py          # reconcile_pending_payments
│   │   │   └── subscriptions.py     # subscription_expiration_notifications
│   │   └── bot_sender.py            # Bot(token) singleton + send helpers
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       └── ...
│
├── docker-compose.yml
├── docker-compose.override.yml      # dev-overrides (volumes, ports)
├── .env.example
├── .gitignore
├── README.md
├── Makefile                         # make up, make test, make lint, make migrate
└── pyproject.toml                   # root — ruff, pytest config
```

---

## §4. Маппинг файлов: было → стало

### Фаза 1 — переезд целиком (без сплитов)

| Было (монолит) | Стало | Примечание |
|----------------|-------|------------|
| `bot.py` | `bot/bot/main.py` | Убрать scheduler, init_db; добавить httpx client |
| `config.py` | `shared/zoo_shared/config.py` | Pydantic `BaseSettings` |
| `database.py` | `shared/zoo_shared/db/engine.py` | Убрать `init_db()` / `_ensure_schema()` |
| `models/models.py` | `shared/zoo_shared/db/models.py` | Целиком |
| `handlers/*.py` (все 17) | `bot/bot/handlers/*.py` | Целиком; в Фазе 2 — заменить `async_session` → `api_client` |
| `keyboards/keyboards.py` | `bot/bot/keyboards/keyboards.py` | Целиком |
| `states/states.py` | `bot/bot/states/states.py` | Целиком |
| `middlewares/*.py` | `bot/bot/middlewares/*.py` | Целиком |
| `utils/helpers.py` | `bot/bot/utils/helpers.py` | Целиком |
| `services/scheduler.py` | `worker/worker/tasks/reminders.py` + `worker/worker/main.py` | Split: scheduling logic → tasks/, runner → main.py |
| `services/subscription.py` | `backend/backend/services/subscription.py` | Целиком |
| `services/vision.py` | `backend/backend/services/vision.py` | Целиком |
| `services/voice.py` | `backend/backend/services/voice.py` | Целиком |
| `services/weather.py` | `backend/backend/services/weather.py` | Целиком |
| `services/clinics.py` | `backend/backend/services/clinics.py` | Целиком |
| `services/charts.py` | `backend/backend/services/charts.py` | Целиком |
| `services/norms.py` | `backend/backend/services/norms.py` | Целиком |
| `services/pdf_export.py` | `backend/backend/services/pdf_export.py` | Целиком |
| `services/content.py` | `backend/backend/services/content.py` | Целиком |
| `services/analytics.py` | `backend/backend/services/analytics.py` | Целиком |
| `services/access.py` | `backend/backend/services/access.py` | Целиком |
| `services/provider_health.py` | `backend/backend/services/provider_health.py` | Целиком |

### Удаляемые файлы

| Файл | Причина |
|------|---------|
| `deploy.sh` | Заменяется GitHub Actions + docker compose |
| `setup-ssh.sh` | Не нужен в CD-пайплайне |
| `zoo_bot.service` | Заменяется docker compose |
| `DEPLOY.md` | Переписывается под docker compose |
| `bot.log.1` | Лог-файл (не код) |
| `.claude/` | Не относится к проекту |

### Новые файлы (создаёт исполнитель)

| Файл | Назначение |
|------|-----------|
| `shared/pyproject.toml` | Пакет zoo_shared |
| `shared/zoo_shared/schemas/*.py` | Pydantic-схемы для bot↔backend |
| `bot/bot/api_client.py` | httpx-клиент к backend |
| `backend/backend/main.py` | FastAPI app |
| `backend/backend/deps.py` | DI: get_session |
| `backend/backend/routers/*.py` | REST endpoints |
| `worker/worker/main.py` | APScheduler entrypoint |
| `worker/worker/bot_sender.py` | Bot(token) singleton |
| `worker/worker/tasks/*.py` | Фоновые задачи |
| `alembic/` | Всё содержимое |
| `docker/*.Dockerfile` | 3 Dockerfile |
| `docker-compose.yml` | Оркестрация |
| `.github/workflows/deploy.yml` | CD |
| `Makefile` | Dev-команды |

---

## §5. docker-compose.yml (черновик)

```yaml
version: "3.9"

x-shared-env: &shared-env
  DATABASE_URL: postgresql+asyncpg://zoo:${POSTGRES_PASSWORD}@postgres:5432/zoo_bot
  REDIS_URL: redis://redis:6379/0

services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: zoo_bot
      POSTGRES_USER: zoo
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U zoo"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --save 60 1 --loglevel warning
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: docker/backend.Dockerfile
    restart: unless-stopped
    environment:
      <<: *shared-env
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
      OPENROUTER_MODEL: ${OPENROUTER_MODEL:-openai/gpt-4o-mini}
      OPENROUTER_BASE_URL: ${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}
      OPENROUTER_SITE_URL: ${OPENROUTER_SITE_URL:-}
      OPENROUTER_APP_NAME: ${OPENROUTER_APP_NAME:-zoo_bot}
      OPENAI_MODEL: ${OPENAI_MODEL:-gpt-4o-mini}
      OPENAI_TRANSCRIBE_MODEL: ${OPENAI_TRANSCRIBE_MODEL:-whisper-1}
      WEATHER_API_KEY: ${WEATHER_API_KEY:-}
      YOOKASSA_SHOP_ID: ${YOOKASSA_SHOP_ID:-}
      YOOKASSA_SECRET_KEY: ${YOOKASSA_SECRET_KEY:-}
      RECEIPT_EMAIL: ${RECEIPT_EMAIL:-}
      PAYMENT_RETURN_URL: ${PAYMENT_RETURN_URL:-}
      FREE_AI_LIMIT: ${FREE_AI_LIMIT:-10}
      FREE_PET_LIMIT: ${FREE_PET_LIMIT:-2}
      AI_MAX_TOKENS_VISION: ${AI_MAX_TOKENS_VISION:-1600}
      AI_MAX_TOKENS_TEXT: ${AI_MAX_TOKENS_TEXT:-1800}
      ADMIN_IDS: ${ADMIN_IDS:-}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      retries: 3

  bot:
    build:
      context: .
      dockerfile: docker/bot.Dockerfile
    restart: unless-stopped
    environment:
      <<: *shared-env
      BOT_TOKEN: ${BOT_TOKEN}
      BACKEND_URL: http://backend:8000
      BOT_TIMEZONE: ${BOT_TIMEZONE:-Europe/Moscow}
    depends_on:
      backend:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    build:
      context: .
      dockerfile: docker/worker.Dockerfile
    restart: unless-stopped
    environment:
      <<: *shared-env
      BOT_TOKEN: ${BOT_TOKEN}
      BOT_TIMEZONE: ${BOT_TIMEZONE:-Europe/Moscow}
      WEATHER_API_KEY: ${WEATHER_API_KEY:-}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  pg_data:
  redis_data:
```

### Пример: `docker/backend.Dockerfile`

```dockerfile
FROM python:3.11-slim AS base

WORKDIR /app

# Shared package
COPY shared/ shared/
RUN pip install --no-cache-dir -e shared/

# Backend
COPY backend/ backend/
RUN pip install --no-cache-dir -e backend/

# Alembic
COPY alembic/ alembic/
COPY alembic/alembic.ini .

# Fonts for PDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core curl && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
```

---

## §6. .env.example + .gitignore

### .env.example

```env
# ══════ REQUIRED ══════
BOT_TOKEN=
POSTGRES_PASSWORD=changeme

# ══════ DATABASE ══════
DATABASE_URL=postgresql+asyncpg://zoo:${POSTGRES_PASSWORD}@postgres:5432/zoo_bot
REDIS_URL=redis://redis:6379/0

# ══════ AI PROVIDERS (optional) ══════
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_TRANSCRIBE_MODEL=whisper-1
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_SITE_URL=
OPENROUTER_APP_NAME=zoo_bot

# ══════ FEATURES ══════
BOT_TIMEZONE=Europe/Moscow
WEATHER_API_KEY=
ADMIN_IDS=

# ══════ LIMITS ══════
FREE_AI_LIMIT=10
FREE_PET_LIMIT=2
AI_MAX_TOKENS_VISION=1600
AI_MAX_TOKENS_TEXT=1800

# ══════ PAYMENTS (optional) ══════
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
RECEIPT_EMAIL=
PAYMENT_RETURN_URL=

# ══════ INTERNAL (auto in docker-compose, manual for local dev) ══════
BACKEND_URL=http://backend:8000
```

### .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
*.egg-info/
dist/
build/
.eggs/

# Virtual environments
venv/
.venv/
env/

# Environment & secrets
.env
*.env.local

# Database
*.db
*.sqlite3

# Logs
*.log
*.log.*

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Docker volumes (local)
pg_data/
redis_data/

# Coverage
htmlcov/
.coverage
.coverage.*

# Pytest
.pytest_cache/

# Alembic
alembic/versions/__pycache__/

# Misc
.claude/
```

---

## §7. GitHub Actions CD workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to VPS

on:
  push:
    branches: [main]

concurrency:
  group: deploy-prod
  cancel-in-progress: false

env:
  DEPLOY_PATH: /opt/zoo_bot

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: zoo_test
          POSTGRES_USER: zoo
          POSTGRES_PASSWORD: testpass
        ports: ["5432:5432"]
        options: >-
          --health-cmd="pg_isready -U zoo"
          --health-interval=5s
          --health-retries=5
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
        options: >-
          --health-cmd="redis-cli ping"
          --health-interval=5s
          --health-retries=5
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install deps
        run: |
          pip install -e shared/ -e backend/ -e bot/ -e worker/
          pip install pytest pytest-cov pytest-asyncio httpx

      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://zoo:testpass@localhost:5432/zoo_test
          REDIS_URL: redis://localhost:6379/0
          BOT_TOKEN: fake:token
          BACKEND_URL: http://localhost:8000
        run: |
          pytest --cov=shared --cov=backend --cov=bot --cov=worker \
                 --cov-report=term-missing --cov-fail-under=75

      - name: Lint
        run: |
          pip install ruff
          ruff check .

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd ${{ env.DEPLOY_PATH }}
            git pull origin main
            docker compose up -d --build --remove-orphans
            docker compose exec backend alembic upgrade head
            docker image prune -f
```

**GitHub Secrets, которые нужно задать:**

| Secret | Назначение |
|--------|-----------|
| `VPS_HOST` | IP или домен сервера |
| `VPS_USER` | SSH-пользователь |
| `VPS_SSH_KEY` | Приватный SSH-ключ |

> На сервере должен быть docker compose + git clone репозитория в `/opt/zoo_bot` + `.env` файл.

---

## §8. Дорожная карта по фазам

---

### Фаза 0: Git + Cleanup (≈1 день)

**Цель:** Чистый main — готовый к рефакторингу.

- [x] Создать ветку `refactor/phase-0-cleanup` от `main`
- [x] Добавить корневой `.gitignore` (из §6)
- [x] Удалить `bot.log.1` из репо (git rm)
- [x] Удалить `.claude/` из репо
- [x] Удалить `setup-ssh.sh` (будет CD)
- [x] Добавить корневой `pyproject.toml` с конфигурацией ruff
- [x] `ruff check .` на текущем коде — исправить критичные ошибки (если есть)
- [x] PR → main, ревью

---

### Фаза 1: Структура каталогов + shared (≈2-3 дня)

**Цель:** Новая файловая структура. Код перенесён, но ещё работает «по-старому» внутри каждого сервиса. Сплитов нет.

- [x] Ветка `refactor/phase-1-structure`
- [x] Создать `shared/pyproject.toml` и `shared/zoo_shared/`:
  - `config.py` — перевести на Pydantic `BaseSettings`
  - `db/engine.py` — engine + sessionmaker (из `database.py`)
  - `db/models.py` — все модели (из `models/models.py`)
- [x] Создать заготовки `shared/zoo_shared/schemas/` (пустые Pydantic-модели — наполнять в Фазе 2)
- [x] Создать `bot/pyproject.toml`, перенести handler/keyboard/state/middleware/utils → `bot/bot/`
- [x] Создать `backend/pyproject.toml`, перенести services/ → `backend/backend/services/`
- [x] Создать заготовку `backend/backend/main.py` (пустой FastAPI app)
- [x] Создать `worker/pyproject.toml`, вынести scheduler.py → `worker/worker/tasks/`
- [x] Обновить все `import` пути
- [x] `bot/bot/main.py` — временно: `from zoo_shared.db.engine import async_session` + `init_db()`. Бот ещё ходит в БД напрямую (убираем в Фазе 2)
- [x] Проверить: `python -m bot.bot.main` стартует (polling) с SQLite
- [x] PR → main, ревью

---

### Фаза 2: Разделение сервисов (≈5-7 дней)

**Цель:** Bot → httpx → Backend → DB. Worker → DB напрямую. Все сервисы автономны.

- [x] Ветка `refactor/phase-2-services`
- [x] **Backend routers**: реализовать REST API (CRUD) для каждого домена
- [x] **`bot/bot/api_client.py`**: httpx AsyncClient wrapper для всех endpoint'ов backend'а
- [x] **Перевести handlers**: заменить `async with async_session()` → `await api_client.get_pets(user_id)` etc.
- [x] **Worker**: `worker/worker/main.py` — APScheduler + `Bot(token)` singleton
- [x] Удалить `bot.py`, `database.py`, `config.py`, `models/`, `services/` из корня
- [x] Локальный smoke-test: запустить backend, потом bot, проверить `/start`
- [x] PR → main, ревью

---

### Фаза 3: Docker Compose (≈2-3 дня)

**Цель:** `docker compose up -d` запускает всё.

- [ ] Ветка `refactor/phase-3-docker`
- [ ] Создать `docker/bot.Dockerfile`, `docker/backend.Dockerfile`, `docker/worker.Dockerfile`
- [ ] Создать `docker-compose.yml` (из §5)
- [ ] Создать `docker-compose.override.yml` для dev (volume mounts, debug ports)
- [ ] **Alembic setup**:
  - `alembic init alembic`
  - Настроить `env.py` → `from zoo_shared.db.models import Base`
  - `alembic revision --autogenerate -m "initial"` → первая миграция
  - Проверить: `docker compose up -d && docker compose exec backend alembic upgrade head`
- [ ] Обновить `.env.example` (из §6)
- [ ] Создать `Makefile`
- [ ] Smoke-test: `docker compose up -d`, отправить `/start` боту
- [ ] Обновить `README.md` под новую архитектуру
- [ ] PR → main, ревью

---

### Фаза 4: Тесты — покрытие 75% (≈5-7 дней)

**Цель:** `pytest --cov-fail-under=75` проходит.

- [ ] Ветка `refactor/phase-4-tests`
- [ ] **Приоритеты тестирования** (от high-impact к low):
  1. `shared/zoo_shared/db/models.py` — unit-тесты моделей (age_str, category_emoji, etc.)
  2. `backend/backend/services/subscription.py` — логика тарифов, лимитов
  3. `backend/backend/services/norms.py` — расчёт норм (чистые функции)
  4. `backend/backend/routers/` — integration-тесты (httpx + TestClient + test DB)
  5. `bot/bot/utils/helpers.py` — парсинг (чистые функции)
  6. `bot/bot/api_client.py` — mock httpx
  7. `worker/worker/tasks/` — mock Bot, mock DB session
  8. `backend/backend/services/charts.py` — smoke (возвращает bytes)
  9. `backend/backend/services/pdf_export.py` — smoke
  10. `backend/backend/services/analytics.py` — unit
- [ ] Настроить `conftest.py`
- [ ] Написать тесты (цель: ≥75% coverage по каждому пакету)
- [ ] Добавить в `pyproject.toml` pytest-cov настройки
- [ ] `pytest --cov-report=term-missing` — убедиться ≥75%
- [ ] PR → main, ревью

---

### Фаза 5: CD + Smoke на проде (≈1-2 дня)

**Цель:** Push в main → автоматический деплой → бот работает в проде.

- [ ] Ветка `refactor/phase-5-cd`
- [ ] Добавить `.github/workflows/deploy.yml` (из §7)
- [ ] На сервере (архитектор по SSH):
  - [ ] Установить Docker + docker compose
  - [ ] `git clone` репозитория в `/opt/zoo_bot`
  - [ ] Создать `.env` с реальными секретами
  - [ ] `docker compose up -d` — первый запуск
  - [ ] Проверить миграцию: `docker compose exec backend alembic upgrade head`
- [ ] Задать GitHub Secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`
- [ ] Push → GitHub Actions → deploy
- [ ] Smoke-test в Telegram
- [ ] Удалить старый `zoo_bot.service`, остановить старый systemd-сервис
- [ ] PR → main, ревью
