#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/opt/zoo_bot"
BACKUP_DIR="$BASE_DIR/backups"
DB_FILE="$BASE_DIR/zoo_bot.db"
TS=$(date +"%Y%m%d_%H%M%S")

mkdir -p "$BACKUP_DIR"

if [ -f "$DB_FILE" ]; then
  cp "$DB_FILE" "$BACKUP_DIR/zoo_bot_${TS}.db"
fi

ls -1t "$BACKUP_DIR"/zoo_bot_*.db 2>/dev/null | tail -n +31 | xargs -r rm -f
