#!/usr/bin/env bash
set -euo pipefail

# 停止并移除 qq-bot-notifier systemd 服务（不会删除项目目录、配置和日志）。
# 用法：sudo bash deploy/linux/uninstall-systemd.sh

SERVICE_NAME="qq-bot-notifier"
TARGET="/etc/systemd/system/${SERVICE_NAME}.service"

sudo systemctl disable --now "${SERVICE_NAME}" >/dev/null 2>&1 || true
sudo rm -f "${TARGET}"
sudo systemctl daemon-reload
sudo systemctl reset-failed "${SERVICE_NAME}" >/dev/null 2>&1 || true

echo "Uninstalled ${SERVICE_NAME}"
