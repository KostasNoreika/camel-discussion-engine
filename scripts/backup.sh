#!/bin/bash
set -e

BACKUP_DIR="/opt/backups/camel-discussion"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup SQLite database
echo "📦 Backing up database..."
docker exec camel-discussion-api \
    sqlite3 /app/data/discussions.db \
    ".backup /app/data/backup_${TIMESTAMP}.db"

docker cp camel-discussion-api:/app/data/backup_${TIMESTAMP}.db \
    "$BACKUP_DIR/discussions_${TIMESTAMP}.db"

# Backup logs
echo "📦 Backing up logs..."
docker cp camel-discussion-api:/app/logs \
    "$BACKUP_DIR/logs_${TIMESTAMP}/"

# Compress
tar -czf "$BACKUP_DIR/backup_${TIMESTAMP}.tar.gz" \
    "$BACKUP_DIR/discussions_${TIMESTAMP}.db" \
    "$BACKUP_DIR/logs_${TIMESTAMP}/"

# Cleanup temporary files
rm -rf "$BACKUP_DIR/discussions_${TIMESTAMP}.db"
rm -rf "$BACKUP_DIR/logs_${TIMESTAMP}/"

echo "✅ Backup complete: backup_${TIMESTAMP}.tar.gz"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete
