#!/bin/bash
# Один раз настраивает доступ по SSH-ключу к VPS (чтобы не вводить пароль при деплое).
# Запустите, подставьте в переменные ниже свой хост и пользователя.

set -e

VPS_HOST="${1:-ВАШ_IP_ИЛИ_ДОМЕН}"
VPS_USER="${2:-root}"
KEY_FILE="${HOME}/.ssh/id_ed25519"
PUB_FILE="${HOME}/.ssh/id_ed25519.pub"

echo "🔑 Настройка SSH-ключа для ${VPS_USER}@${VPS_HOST}"
echo ""

if [[ "$VPS_HOST" == "ВАШ_IP_ИЛИ_ДОМЕН" ]]; then
  echo "Использование: $0 IP_ИЛИ_ДОМЕН [ПОЛЬЗОВАТЕЛЬ]"
  echo "Пример:       $0 123.45.67.89 root"
  exit 1
fi

# Есть ли ключ
if [[ ! -f "$PUB_FILE" ]]; then
  echo "Ключ не найден. Создаю: $KEY_FILE"
  ssh-keygen -t ed25519 -C "zoo_bot_deploy" -f "$KEY_FILE" -N ""
  echo ""
fi

echo "Копирую ключ на сервер (один раз введите пароль):"
ssh-copy-id -i "$PUB_FILE" "${VPS_USER}@${VPS_HOST}"

echo ""
echo "✅ Готово. Проверка входа без пароля:"
if ssh -o BatchMode=yes "${VPS_USER}@${VPS_HOST}" "echo OK" 2>/dev/null; then
  echo "   Вход по ключу работает. deploy.sh больше не будет спрашивать пароль."
else
  echo "   Не удалось войти без пароля. Проверьте, что ssh-copy-id выполнился без ошибок."
fi
