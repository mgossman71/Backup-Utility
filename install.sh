#!/usr/bin/env bash
# MountGuard Backup — one-shot installer for Ubuntu/Debian.
#
#   sudo ./install.sh
#
# Installs system deps, builds a virtualenv, writes a systemd service, and starts
# it. It backs up paths ON THIS HOST. The web UI is reachable on all interfaces
# by default (http://<this-host>:8009) — keep that on a trusted LAN/VPN or
# firewall it. Docker is NOT required for this path (it is the recommended one).
set -euo pipefail

APP="mountguard-backup"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$REPO_DIR/.venv"
ENV_FILE="/etc/${APP}.env"
UNIT="/etc/systemd/system/${APP}.service"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root so rsync can read sources and write to the destination:" >&2
  echo "    sudo ./install.sh" >&2
  exit 1
fi

echo "==> Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
  rsync python3 python3-venv python3-pip python3-dev ca-certificates

echo "==> Creating virtualenv at $VENV"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet -r "$REPO_DIR/requirements.txt"

echo "==> Writing config to $ENV_FILE (existing file left untouched)"
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<'EOF'
# MountGuard Backup configuration (sourced by run.sh / systemd).
BACKUP_UI_HOST=0.0.0.0
BACKUP_UI_PORT=8009
BACKUP_UI_STATE_DIR=/var/lib/backup-ui
BACKUP_UI_LOG_DIR=/var/log/backup-ui
BACKUP_UI_TIMEZONE=America/Chicago
BACKUP_UI_RSYNC=rsync
EOF
fi

chmod +x "$REPO_DIR/run.sh"

echo "==> Installing systemd unit -> $UNIT"
cat > "$UNIT" <<EOF
[Unit]
Description=MountGuard Backup dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=$REPO_DIR/run.sh
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

mkdir -p /var/lib/backup-ui /var/log/backup-ui
systemctl daemon-reload
systemctl enable "$APP"
systemctl restart "$APP"
sleep 1

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo
echo "==> Installed and running."
echo "    Open the dashboard in a browser:  http://${IP:-<this-host>}:$(grep -E '^BACKUP_UI_PORT=' "$ENV_FILE" | cut -d= -f2)"
echo "    Then click 'Create Backup Job'."
echo "    Manage the service:  systemctl status $APP   (or: journalctl -u $APP -f)"
