#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LABEL="com.sevenpirates.bot-notifier"
TARGET_DIR="${HOME}/Library/LaunchAgents"
TARGET_PLIST="${TARGET_DIR}/${LABEL}.plist"
TEMPLATE="${SCRIPT_DIR}/${LABEL}.plist.template"

if [[ ! -x "${PROJECT_DIR}/env/bin/python" ]]; then
  echo "Missing executable Python: ${PROJECT_DIR}/env/bin/python" >&2
  echo "Create the macOS virtualenv first, for example: python3 -m venv env" >&2
  exit 1
fi

mkdir -p "${TARGET_DIR}" "${PROJECT_DIR}/logs"
ESCAPED_PROJECT_DIR="$(printf '%s\n' "${PROJECT_DIR}" | sed -e 's/[#&]/\\&/g')"
sed "s#__PROJECT_DIR__#${ESCAPED_PROJECT_DIR}#g" "${TEMPLATE}" > "${TARGET_PLIST}"

launchctl bootout "gui/$(id -u)" "${TARGET_PLIST}" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "${TARGET_PLIST}"
launchctl enable "gui/$(id -u)/${LABEL}"
launchctl kickstart -k "gui/$(id -u)/${LABEL}"

echo "Installed and started ${LABEL}"
echo "Plist: ${TARGET_PLIST}"
echo "Logs: ${PROJECT_DIR}/logs/launchd.out.log and ${PROJECT_DIR}/logs/launchd.err.log"
