#!/usr/bin/env bash
# Ежедневный бэкап БД zoo_bot. Ротация 7 дней. Ставится в cron под zoo-core.
set -euo pipefail

PROJECT_DIR="/opt/zoo_bot"
BACKUP_DIR="${PROJECT_DIR}/backups"
RETENTION_DAYS=7
STAMP="$(date +%F_%H%M)"
OUT="${BACKUP_DIR}/zoo_bot_${STAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"
cd "${PROJECT_DIR}"

# pg_dump из работающего контейнера → gzip. -T: без TTY (cron).
docker compose exec -T postgres pg_dump -U zoo -d zoo_bot | gzip -9 > "${OUT}"

# Проверка целостности архива; битый — удаляем, выходим с ошибкой.
if ! gzip -t "${OUT}" 2>/dev/null; then
    echo "$(date -Is) BACKUP CORRUPT: ${OUT}" >&2
    rm -f "${OUT}"
    exit 1
fi

# Ротация: старше RETENTION_DAYS — удалить.
find "${BACKUP_DIR}" -name 'zoo_bot_*.sql.gz' -mtime "+${RETENTION_DAYS}" -delete

echo "$(date -Is) BACKUP OK: ${OUT} ($(du -h "${OUT}" | cut -f1))"
