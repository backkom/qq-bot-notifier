#!/usr/bin/env bash
set -euo pipefail

LABEL="com.sevenpirates.bot-notifier"
TARGET_PLIST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
DOMAIN="gui/$(id -u)"

if [[ ! -f "${TARGET_PLIST}" ]]; then
  echo "LaunchAgent plist not found: ${TARGET_PLIST}" >&2
  echo "Run deploy/macos/install-launchctl.sh first." >&2
  exit 1
fi

launchctl bootout "${DOMAIN}" "${TARGET_PLIST}" >/dev/null 2>&1 || true
launchctl bootstrap "${DOMAIN}" "${TARGET_PLIST}"
launchctl enable "${DOMAIN}/${LABEL}"
launchctl kickstart -k "${DOMAIN}/${LABEL}"

echo "Restarted ${LABEL}"
echo "Plist: ${TARGET_PLIST}"
