#!/usr/bin/env bash
# ==============================================================================
# Jarvis VPS 24/7 Deployment Script (Hostinger / Ubuntu / Debian)
# Steps 01 & 02: Deploy and run Jarvis 24/7 on a cloud VPS server
# ==============================================================================

set -e

echo "=========================================================="
echo " Starting Jarvis Autonomous AI Deployment (VPS 24/7)"
echo " Brain: Google Gemini 2.5 Flash / Pro"
echo " Channels: Web Dashboard + Telegram Mobile Bridge"
echo "=========================================================="

# Check root or sudo
if [ "$EUID" -ne 0 ]; then
    echo "[!] Please run with sudo or as root: sudo bash scripts/deploy_vps.sh"
    exit 1
fi

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CURRENT_USER="${SUDO_USER:-$USER}"

echo "[1/6] Updating system repositories & installing packages..."
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git curl build-essential libnotify-bin

echo "[2/6] Configuring Python Virtual Environment at ${APP_DIR}/venv..."
if [ ! -d "${APP_DIR}/venv" ]; then
    python3 -m venv "${APP_DIR}/venv"
fi

echo "[3/6] Installing dependencies..."
"${APP_DIR}/venv/bin/pip" install --upgrade pip
if [ -f "${APP_DIR}/requirements.txt" ]; then
    "${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
fi

echo "[4/6] Ensuring environment configuration (.env)..."
if [ ! -f "${APP_DIR}/.env" ]; then
    if [ -f "${APP_DIR}/.env.example" ]; then
        cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
        chown "${CURRENT_USER}:${CURRENT_USER}" "${APP_DIR}/.env"
        echo "[*] Created .env from .env.example. Please populate GEMINI_API_KEY and TELEGRAM_BOT_TOKEN."
    fi
fi

echo "[5/6] Installing systemd services..."
# Populate user and directory in unit files
sed -e "s|User=.*|User=${CURRENT_USER}|g" \
    -e "s|WorkingDirectory=.*|WorkingDirectory=${APP_DIR}|g" \
    -e "s|EnvironmentFile=.*|EnvironmentFile=${APP_DIR}/.env|g" \
    -e "s|ExecStart=.*uvicorn|ExecStart=${APP_DIR}/venv/bin/uvicorn|g" \
    "${APP_DIR}/deployment/jarvis-api.service" > /etc/systemd/system/jarvis-api.service

sed -e "s|User=.*|User=${CURRENT_USER}|g" \
    -e "s|WorkingDirectory=.*|WorkingDirectory=${APP_DIR}|g" \
    -e "s|EnvironmentFile=.*|EnvironmentFile=${APP_DIR}/.env|g" \
    -e "s|ExecStart=.*python|ExecStart=${APP_DIR}/venv/bin/python|g" \
    "${APP_DIR}/deployment/jarvis-daemon.service" > /etc/systemd/system/jarvis-daemon.service

systemctl daemon-reload
systemctl enable jarvis-api.service
systemctl enable jarvis-daemon.service

echo "[6/6] Reloaded services."
echo "----------------------------------------------------------"
echo "Deployment Complete!"
echo "Commands to manage your Jarvis 24/7 Agent:"
echo "  Start:   sudo systemctl start jarvis-api jarvis-daemon"
echo "  Status:  sudo systemctl status jarvis-api jarvis-daemon"
echo "  Logs:    sudo journalctl -u jarvis-daemon -f"
echo "  Stop:    sudo systemctl stop jarvis-api jarvis-daemon"
echo "----------------------------------------------------------"

