#!/usr/bin/env bash
# Start MountGuard Backup. Reads /etc/mountguard-backup.env if present so host
# and port have a single source of truth (also used by the systemd service).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f /etc/mountguard-backup.env ]; then
  set -a
  . /etc/mountguard-backup.env
  set +a
fi
cd "$DIR"
exec "$DIR/.venv/bin/uvicorn" app.main:app \
  --host "${BACKUP_UI_HOST:-0.0.0.0}" \
  --port "${BACKUP_UI_PORT:-8009}"
