#!/usr/bin/env bash
# Remove the MountGuard Backup systemd service. Leaves jobs/logs on disk unless
# you pass --purge.
#   sudo ./uninstall.sh          # stop + remove service, keep data
#   sudo ./uninstall.sh --purge  # also delete state (jobs DB) and run logs
set -euo pipefail
APP="mountguard-backup"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: sudo ./uninstall.sh [--purge]" >&2
  exit 1
fi

systemctl disable --now "$APP" 2>/dev/null || true
rm -f "/etc/systemd/system/${APP}.service"
systemctl daemon-reload
echo "==> Service removed."

if [ "${1:-}" = "--purge" ]; then
  rm -rf /var/lib/backup-ui /var/log/backup-ui "/etc/${APP}.env"
  echo "==> Purged state, logs, and config."
else
  echo "==> Kept /var/lib/backup-ui and /var/log/backup-ui (use --purge to remove)."
fi
