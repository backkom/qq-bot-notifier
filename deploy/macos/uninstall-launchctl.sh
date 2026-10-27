#!/usr/bin/env bash
set -euo pipefail

LABEL="com.leaf.bot-notifier"
TARGET_PLIST="${HOME}/Library/LaunchAgents/${LABEL}.plist"

launchctl bootout "gui/$(id -u)" "${TARGET_PLIST}" >/dev/null 2>&1 || true
rm -f "${TARGET_PLIST}"

echo "Uninstalled ${LABEL}"
