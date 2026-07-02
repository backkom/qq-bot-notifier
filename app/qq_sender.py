from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any

import httpx

from .env_loader import load_project_env
from .models import QQBotConfig


class QQBotSendError(RuntimeError):
    pass


load_project_env()

DELIVERY_LOG_PATH = Path(os.getenv("QQ_DELIVERY_LOG", "logs/qqbot-payloads.jsonl"))
_DELIVERY_LOG_LOCK = RLock()


async def send_group_message(
    qq_bot: QQBotConfig,
    group_id: int,
    message: list[dict[str, Any]],
) -> int:
    headers = {"Content-Type": "application/json"}
    if qq_bot.token:
        headers["Authorization"] = f"Bearer {qq_bot.token}"

    payload = {
        "group_id": group_id,
        "message": message,
    }

    write_delivery_log(qq_bot.url, payload)

    async with httpx.AsyncClient(timeout=qq_bot.timeout_seconds) as client:
        response = await client.post(qq_bot.url, headers=headers, json=payload)

    if response.status_code >= 400:
        raise QQBotSendError(f"QQ bot returned {response.status_code}: {response.text[:500]}")

    return response.status_code


def write_delivery_log(url: str, payload: dict[str, Any]) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "payload": payload,
    }
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))

    with _DELIVERY_LOG_LOCK:
        DELIVERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DELIVERY_LOG_PATH.open("a", encoding="utf-8") as file:
            file.write(line + "\n")


def read_recent_delivery_logs(hours: int = 24, limit: int = 100) -> list[dict[str, Any]]:
    if not DELIVERY_LOG_PATH.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    records: list[dict[str, Any]] = []

    with _DELIVERY_LOG_LOCK:
        lines = DELIVERY_LOG_PATH.read_text(encoding="utf-8").splitlines()

    for line in reversed(lines):
        try:
            entry = json.loads(line)
            timestamp = _parse_log_timestamp(entry.get("timestamp", ""))
        except (json.JSONDecodeError, ValueError, TypeError):
            continue

        if timestamp < cutoff:
            continue

        payload = entry.get("payload", {})
        records.append(
            {
                "timestamp": timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
                "url": entry.get("url", ""),
                "group_id": payload.get("group_id", ""),
                "message_preview": _message_preview(payload.get("message", [])),
            }
        )
        if len(records) >= limit:
            break

    return records


def _parse_log_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _message_preview(message: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for segment in message:
        data = segment.get("data", {})
        if segment.get("type") == "at":
            parts.append(f"@{data.get('qq', '')}")
        elif segment.get("type") == "text":
            parts.append(str(data.get("text", "")))
        else:
            parts.append(f"[{segment.get('type', 'unknown')}]")

    preview = " ".join(part for part in parts if part).strip()
    if len(preview) > 180:
        return preview[:177] + "..."
    return preview
