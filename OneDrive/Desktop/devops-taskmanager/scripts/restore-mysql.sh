#!/usr/bin/env bash
# Usage: ./restore-mysql.sh backups/taskmgr-YYYYmmdd-HHMMSS.sql.gz
set -euo pipefail

FILE="${1:?Usage: $0 <backup.sql.gz>}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/taskmgr}"
[ -f "$FILE" ] || { echo "Backup not found: $FILE" >&2; exit 1; }

read -r -p "This overwrites the current database with $FILE. Continue? [y/N] " answer
[ "$answer" = "y" ] || { echo "Aborted."; exit 1; }

cd "$DEPLOY_DIR"
gunzip -c "$FILE" | docker compose exec -T db sh -c \
    'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -u root "$MYSQL_DATABASE"'
echo "Restore complete."
