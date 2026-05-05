#!/bin/bash
# Деплой ZooBuddy на VPS: заливка файлов через rsync.
# Перед запуском отредактируйте переменные ниже.

set -e

# ---------- НАСТРОЙКИ (подставьте свои значения) ----------
VPS_HOST="ВАШ_IP_ИЛИ_ДОМЕН"
VPS_USER="root"
APP_DIR="/opt/zoo_bot"
# ---------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RSYNC_EXCLUDE="--exclude=venv --exclude=.env --exclude=*.db --exclude=__pycache__ --exclude=*.log --exclude=.git"

echo "📦 Деплой ZooBuddy на ${VPS_USER}@${VPS_HOST}:${APP_DIR}"
echo ""

# Проверка настроек
if [[ "$VPS_HOST" == "ВАШ_IP_ИЛИ_ДОМЕН" ]]; then
  echo "❌ Отредактируйте deploy.sh: укажите VPS_HOST, VPS_USER и при необходимости APP_DIR"
  exit 1
fi

# Создание каталога на сервере
ssh "${VPS_USER}@${VPS_HOST}" "mkdir -p ${APP_DIR}"

# Заливка файлов
echo "📤 Копирование файлов..."
rsync -avz $RSYNC_EXCLUDE "${SCRIPT_DIR}/" "${VPS_USER}@${VPS_HOST}:${APP_DIR}/"

echo "✅ Файлы залиты."
echo ""
echo "Дальше на сервере выполните:"
echo "  ssh ${VPS_USER}@${VPS_HOST}"
echo "  cd ${APP_DIR}"
echo "  python3 -m venv venv && source venv/bin/activate"
echo "  pip install -r requirements.txt"
echo "  cp .env.example .env && nano .env   # вставьте BOT_TOKEN"
echo "  sudo cp zoo_bot.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload && sudo systemctl enable zoo_bot && sudo systemctl start zoo_bot"
echo ""
echo "Подробно: см. DEPLOY.md"
