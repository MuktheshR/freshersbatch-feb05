#!/usr/bin/env bash
# Logical MySQL backup with retention and optional S3 upload.
# Cron example (daily 02:00): 0 2 * * * /opt/taskmgr/backup-mysql.sh >> /opt/taskmgr/backups/backup.log 2>&1
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/taskmgr}"
BACKUP_DIR="${BACKUP_DIR:-$DEPLOY_DIR/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
S3_BUCKET="${S3_BUCKET:-}"

cd "$DEPLOY_DIR"
mkdir -p "$BACKUP_DIR"
FILE="$BACKUP_DIR/taskmgr-$(date +%Y%m%d-%H%M%S).sql.gz"

# --single-transaction gives a consistent InnoDB snapshot without locking tables.
docker compose exec -T db sh -c \
    'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -u root --single-transaction --routines --triggers "$MYSQL_DATABASE"' \
    | gzip > "$FILE"

gzip -t "$FILE"
echo "$(date -Is) Backup written: $FILE ($(du -h "$FILE" | cut -f1))"

if [ -n "$S3_BUCKET" ]; then
    aws s3 cp "$FILE" "s3://$S3_BUCKET/mysql/$(basename "$FILE")"
    echo "$(date -Is) Uploaded to s3://$S3_BUCKET/mysql/"
fi

find "$BACKUP_DIR" -name 'taskmgr-*.sql.gz' -mtime +"$RETENTION_DAYS" -print -delete
