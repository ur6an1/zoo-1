# ZooBuddy

Telegram-бот для владельцев домашних животных: учёт питомцев, напоминания, медицинские записи, анализ питания, AI-ассистент и многое другое.

## Архитектура

Проект разделён на 5 контейнеров:

| Сервис | Описание |
|--------|----------|
| **bot** | aiogram Dispatcher — Telegram polling, FSM, handlers. Общается с backend через httpx |
| **backend** | FastAPI REST API — CRUD, бизнес-логика, Alembic-миграции |
| **worker** | APScheduler — фоновые задачи (напоминания, вакцинация, погода, платежи) |
| **postgres** | PostgreSQL 16 |
| **redis** | FSM storage + кэш |

```
┌──────────┐   httpx    ┌──────────┐   asyncpg   ┌──────────┐
│   bot    │──────────→ │ backend  │────────────→ │ postgres │
└──────────┘            └──────────┘              └──────────┘
                              ↑                        ↑
┌──────────┐   shared/db (напрямую)                   │
│  worker  │──────────────────────────────────────────┘
└──────────┘
      ↕
┌──────────┐
│  redis   │
└──────────┘
```

## Быстрый старт

```bash
# 1. Клонировать
git clone https://github.com/mukhacheva01/zoo.git
cd zoo

# 2. Настроить окружение
cp .env.example .env
# Заполнить BOT_TOKEN и POSTGRES_PASSWORD в .env

# 3. Запустить
make up
# или: docker compose up -d --build

# 4. Проверить
docker compose ps
docker compose logs -f
```

## Основные команды

```bash
make up          # Собрать и запустить все контейнеры
make down        # Остановить контейнеры
make logs        # Посмотреть логи всех контейнеров
make migrate     # Применить миграции (alembic upgrade head)
make migration msg="описание"  # Создать новую миграцию
make test        # Запустить тесты с проверкой покрытия
make lint        # Проверка кода (ruff)
make build       # Собрать образы без запуска
```

## Структура проекта

```
zoo/
├── shared/          # Общий пакет zoo_shared (config, models, schemas)
├── bot/             # Telegram-бот (aiogram)
├── backend/         # REST API (FastAPI)
├── worker/          # Фоновые задачи (APScheduler)
├── alembic/         # Миграции БД
├── docker/          # Dockerfiles
├── docs/            # Документация (план рефакторинга и др.)
├── docker-compose.yml
├── docker-compose.override.yml  # Dev-настройки (порты, volume mounts)
├── Makefile
└── .env.example
```

## Разработка

### Локальный запуск без Docker

```bash
# Установить зависимости
pip install -e shared/ -e backend/ -e bot/ -e worker/

# Запустить Postgres и Redis отдельно (или через docker compose up postgres redis)
# Настроить DATABASE_URL и REDIS_URL в .env

# Применить миграции
DATABASE_URL=... alembic upgrade head

# Запустить сервисы в отдельных терминалах:
python -m backend.main    # FastAPI на :8000
python -m bot.main        # Telegram polling
python -m worker.main     # APScheduler
```

### Миграции

```bash
# Создать новую миграцию после изменения моделей
make migration msg="add_new_field"

# Применить
make migrate
```

## Переменные окружения

См. [`.env.example`](.env.example) для полного списка.

**Обязательные:**
- `BOT_TOKEN` — токен Telegram-бота
- `POSTGRES_PASSWORD` — пароль для PostgreSQL

## Документация

- [План рефакторинга](docs/REFACTORING.md) — описание архитектуры, фаз, маппинга файлов
