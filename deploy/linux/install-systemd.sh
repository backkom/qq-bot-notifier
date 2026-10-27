#!/usr/bin/env bash
set -euo pipefail

# 在 Linux 上安装并启动 qq-bot-notifier systemd 服务。
# 用法：
#   sudo bash deploy/linux/install-systemd.sh
# 可用环境变量覆盖：
#   RUN_USER=leaf PORT=7848 PYTHON_BIN=/path/to/python

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SERVICE_NAME="qq-bot-notifier"
TEMPLATE="${SCRIPT_DIR}/${SERVICE_NAME}.service.template"
TARGET="/etc/systemd/system/${SERVICE_NAME}.service"

RUN_USER="${RUN_USER:-$(id -un)}"
PORT="${PORT:-7848}"
PYTHON_BIN="${PYTHON_BIN:-${PROJECT_DIR}/env/bin/python}"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This script targets Linux/systemd; current platform is $(uname -s)." >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not found; this host does not use systemd." >&2
  exit 1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Missing executable Python: ${PYTHON_BIN}" >&2
  echo "Create the Linux virtualenv first:" >&2
  echo "  python3 -m venv env && env/bin/pip install -r requirements.txt" >&2
  exit 1
fi

if [[ ! -f "${PROJECT_DIR}/.env" ]]; then
  echo "Warning: ${PROJECT_DIR}/.env not found." >&2
  echo "QQ_BOT_TOKEN must come from .env or the config file, otherwise sending fails." >&2
fi

if [[ ! -d "${PROJECT_DIR}/logs" ]]; then
  mkdir -p "${PROJECT_DIR}/logs"
fi

TMP_UNIT="$(mktemp)"
trap 'rm -f "${TMP_UNIT}"' EXIT

sed -e "s|__PROJECT_DIR__|${PROJECT_DIR}|g" \
    -e "s|__RUN_USER__|${RUN_USER}|g" \
    -e "s|__PORT__|${PORT}|g" \
    -e "s|__PYTHON_BIN__|${PYTHON_BIN}|g" \
    "${TEMPLATE}" > "${TMP_UNIT}"

sudo install -m 0644 "${TMP_UNIT}" "${TARGET}"
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

echo "Installed ${TARGET}"
echo "User=${RUN_USER} Port=${PORT} Python=${PYTHON_BIN}"
echo
echo "Status:"
sudo systemctl --no-pager --full status "${SERVICE_NAME}" || true
echo
echo "Logs: journalctl -u ${SERVICE_NAME} -f"
echo "Health check: curl -fsS http://127.0.0.1:${PORT}/healthz"
