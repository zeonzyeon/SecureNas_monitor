#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/planb-nas}"
APP_USER="${APP_USER:-pi}"
APP_GROUP="${APP_GROUP:-pi}"
NAS_SERVER="${NAS_SERVER:-192.168.0.204}"
NAS_SHARE="${NAS_SHARE:-PlanB_Media}"
NAS_MOUNT="${NAS_MOUNT:-/mnt/planb_media}"
NAS_CREDENTIALS="${NAS_CREDENTIALS:-/etc/samba/credentials/planb-nas}"
FLASK_PORT="${FLASK_PORT:-5000}"

if [[ -z "${NAS_USERNAME:-}" || -z "${NAS_PASSWORD:-}" ]]; then
  echo "NAS_USERNAME and NAS_PASSWORD are required." >&2
  exit 1
fi

run_sudo() {
  if [[ -n "${SUDO_PASSWORD:-}" ]]; then
    printf '%s\n' "$SUDO_PASSWORD" | sudo -S -p '' "$@"
  else
    sudo "$@"
  fi
}

run_sudo true
run_sudo apt update
run_sudo apt install -y python3-venv python3-pip cifs-utils tailscale

if ! command -v tailscale >/dev/null 2>&1; then
  echo "Tailscale installation failed." >&2
  exit 1
fi

run_sudo mkdir -p "$NAS_MOUNT" "$(dirname "$NAS_CREDENTIALS")"
printf 'username=%s\npassword=%s\n' "$NAS_USERNAME" "$NAS_PASSWORD" | run_sudo tee "$NAS_CREDENTIALS" >/dev/null
run_sudo chmod 600 "$NAS_CREDENTIALS"

FSTAB_LINE="//$NAS_SERVER/$NAS_SHARE $NAS_MOUNT cifs credentials=$NAS_CREDENTIALS,iocharset=utf8,uid=$APP_USER,gid=$APP_GROUP,file_mode=0664,dir_mode=0775,nofail,_netdev 0 0"
if ! grep -Fq "//$NAS_SERVER/$NAS_SHARE $NAS_MOUNT cifs" /etc/fstab; then
  echo "$FSTAB_LINE" | run_sudo tee -a /etc/fstab >/dev/null
fi

run_sudo mount -a
ls -la "$NAS_MOUNT" >/dev/null
cd "$APP_DIR"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp deploy/raspberry-pi.env.example .env
fi

python3 - <<'PY'
from pathlib import Path
import os
import secrets

env_path = Path(".env")
values = {}
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()

updates = {
    "FLASK_DEBUG": "false",
    "FLASK_HOST": "0.0.0.0",
    "FLASK_PORT": os.environ.get("FLASK_PORT", "5000"),
    "SECRET_KEY": values.get("SECRET_KEY") if values.get("SECRET_KEY") and not values.get("SECRET_KEY", "").startswith("replace-") else secrets.token_urlsafe(48),
    "DATABASE_PATH": "instance/events.sqlite3",
    "NAS_MONITOR_PATH": os.environ.get("NAS_MOUNT", "/mnt/planb_media"),
    "NAS_ALLOW_MAPPED_DRIVE": "false",
    "LOGIN_MAX_FAILED_ATTEMPTS": values.get("LOGIN_MAX_FAILED_ATTEMPTS", "3"),
    "LOGIN_BLOCK_MINUTES": values.get("LOGIN_BLOCK_MINUTES", "10"),
    "ADMIN_USERNAME": values.get("ADMIN_USERNAME", "admin"),
    "ADMIN_PASSWORD": os.environ.get("ADMIN_PASSWORD", values.get("ADMIN_PASSWORD", "change-this-admin-password")),
}

ordered = [
    "FLASK_DEBUG",
    "FLASK_HOST",
    "FLASK_PORT",
    "SECRET_KEY",
    "DATABASE_PATH",
    "NAS_MONITOR_PATH",
    "NAS_ALLOW_MAPPED_DRIVE",
    "LOGIN_MAX_FAILED_ATTEMPTS",
    "LOGIN_BLOCK_MINUTES",
    "ADMIN_USERNAME",
    "ADMIN_PASSWORD",
]
env_path.write_text("\n".join(f"{key}={updates[key]}" for key in ordered) + "\n", encoding="utf-8")
PY

sed \
  -e "s#__APP_USER__#$APP_USER#g" \
  -e "s#__APP_GROUP__#$APP_GROUP#g" \
  -e "s#__APP_DIR__#$APP_DIR#g" \
  -e "s#__FLASK_PORT__#$FLASK_PORT#g" \
  deploy/planb-nas.service | run_sudo tee /etc/systemd/system/planb-nas.service >/dev/null
run_sudo systemctl daemon-reload
run_sudo systemctl enable --now planb-nas
run_sudo systemctl restart planb-nas

echo "Service status:"
systemctl --no-pager --full status planb-nas || true

echo
echo "Tailscale IP:"
tailscale ip -4 || true
